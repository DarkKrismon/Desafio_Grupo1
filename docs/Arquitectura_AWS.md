# Arquitectura de persistencia: PostgreSQL en AWS RDS

> **Estado del documento:** propuesta técnica para Ronda 1
> **Autora del cambio:** Esther Barranco (Data Science)
> **Revisión pendiente:** Ciberseguridad (Guillermo Concepción, Gabriel Maroto, Arantxa Ortega, Javier Domingo) y Full Stack (Karina Paola Rojas, Elena González)
> **Mentor del grupo:** Sergio Fernández

---

## 1. Contexto

La API de detección de fraude **Sentinel** (Blue Team) gestiona actualmente dos estructuras de datos volátiles en memoria, declaradas en `src/storage.py`:

- `_pending_transactions` — diccionario con los casos pendientes de revisión por un analista.
- `_feedback_history` — lista con el feedback histórico de los analistas (casos cerrados).

Estas estructuras se reinicializan en cada arranque del proceso de Uvicorn. Dado que la API se ejecuta dentro de un contenedor Docker en una instancia EC2 de AWS, cualquier reinicio del contenedor, despliegue, fallo del proceso, escalado horizontal o `docker compose down` destruye toda la información operativa.

Este documento define la solución de persistencia que sustituye este almacenamiento volátil, así como el procedimiento de implementación.

---

## 2. Resumen ejecutivo (TL;DR)

| Decisión | Valor |
|---|---|
| **Motor de base de datos** | PostgreSQL 16 |
| **Servicio AWS** | RDS (Relational Database Service) |
| **Región** | `eu-south-2` (Madrid) |
| **Tipo de instancia inicial** | `db.t3.micro` (capa gratuita) |
| **Almacenamiento** | 20 GB gp3 |
| **Tablas** | `transactions`, `fraud_queue`, `analyst_feedback` |
| **Estrategia de migración** | Híbrida: contenedor Postgres en local → RDS en EC2 |
| **ORM en Python** | SQLAlchemy 2.0 + psycopg2 |
| **Variable de configuración** | `DATABASE_URL` (env var) |

---

## 3. Decisión arquitectónica

### 3.1. Por qué PostgreSQL y no otra opción

| Opción evaluada | Veredicto | Motivo |
|---|---|---|
| **SQLite (fichero)** | Descartado | No tiene servicio gestionado en AWS. Limitaciones con accesos concurrentes. Imagen poco profesional ante el jurado. |
| **MongoDB (NoSQL)** | Descartado | Las transacciones son estructuradas y tabulares; el modelo relacional encaja mejor. NovaPay (fintech ficticia) tendría inevitablemente un motor SQL. |
| **MySQL / MariaDB** | Descartado | PostgreSQL ofrece mejor soporte para tipos numéricos exactos (`NUMERIC`), `TIMESTAMP WITH TIME ZONE` y JSONB. Estándar en fintech real. |
| **PostgreSQL** | ✅ **Elegido** | Estándar de la industria, soporte excelente en AWS RDS, gratis en capa free tier, fuerte tipado, compatible con SQLAlchemy. |

### 3.2. Por qué RDS y no Postgres en contenedor

Se evaluaron tres alternativas:

**Opción A — Postgres en contenedor Docker dentro de la misma EC2**

- ✅ Cero coste adicional, todo dentro del free tier de EC2.
- ✅ Configuración rápida (un servicio en `docker-compose.yml`).
- ❌ Sin backups automáticos.
- ❌ Sin alta disponibilidad: si la EC2 cae, Postgres también.
- ❌ Los datos viven en un volumen de Docker dentro de la EC2; si se destruye la EC2, se pierden.
- ❌ El equipo tiene que gestionar parches de seguridad, versiones, retención manualmente.

**Opción B — Postgres en RDS (servicio gestionado de AWS)**

- ✅ Backups automáticos diarios con retención configurable.
- ✅ Snapshots manuales bajo demanda.
- ✅ Parches de seguridad gestionados por AWS.
- ✅ Posibilidad de Multi-AZ para alta disponibilidad (no en free tier).
- ✅ Cumple con los puntos 3 y 4 del PDF de requisitos de Ciberseguridad (*infraestructura segura y escalable, gestión y protección de datos*).
- ❌ Configuración inicial más laboriosa (VPC, security groups, subnets).
- ⚠️ Coste fuera del free tier.

**Opción C — Híbrida: contenedor en desarrollo, RDS en producción**

- ✅ Lo mejor de las dos: rápido para desarrollar y probar localmente, profesional en producción.
- ✅ El código Python no cambia entre entornos (solo cambia la variable `DATABASE_URL`).
- ✅ Permite avanzar sin depender de AWS los primeros días.
- ⚠️ Requiere mantener consistencia entre los dos entornos.

**Decisión: Opción C (híbrida).** Es la que mejor equilibra realismo profesional y velocidad de entrega. Esta documentación cubre la implementación completa de ambas fases.

### 3.3. Justificación ante el jurado del Desafío

Esta arquitectura cubre tres de los criterios de evaluación del PDF de Cívica:

- **Criterio 1 (Aproximación al problema):** demuestra conocimiento de la diferencia entre datos volátiles y persistentes en sistemas en producción.
- **Criterio 2 (Solución al problema):** uso inteligente de tecnología cloud disponible (AWS RDS) sin sobre-ingeniería para una Ronda 1.
- **Criterio 3 (El artefacto):** garantiza que la herramienta del analista sigue funcionando tras reinicios — fiabilidad.

Además, alinea con los **requisitos técnicos de Data Science** del PDF: *"Seleccionar el modelo de base de datos más adecuado, diseñar el esquema, ingestar los datos, desplegar la base de datos con la solución final"*.

---

## 4. Modelo de datos

### 4.1. Esquema relacional

```
┌─────────────────────────────────┐         ┌──────────────────────────┐
│      transactions               │◄────────│    fraud_queue           │
│ (log histórico completo)        │  1───N  │  (casos pendientes)      │
└──────────────┬──────────────────┘         └──────────────────────────┘
               │ 1
               │
               │ N
               ▼
┌─────────────────────────────────┐
│      analyst_feedback           │
│  (casos cerrados por analista)  │
└─────────────────────────────────┘
```

### 4.2. Tabla `transactions`

Guarda **todas** las transacciones que pasan por `POST /fraud/decide`, sea cual sea la decisión final. Es el log histórico y la fuente para reentrenar el modelo en Ronda 2.

| Columna | Tipo | Constraints | Descripción |
|---|---|---|---|
| `transaction_id` | `VARCHAR(50)` | PRIMARY KEY | Identificador que envía NovaPay |
| `amount` | `NUMERIC(12,2)` | NOT NULL, CHECK > 0 | Importe en EUR |
| `type` | `VARCHAR(20)` | NOT NULL | TRANSFER / CASH_OUT / PAYMENT / DEBIT / CASH_IN |
| `oldbalance_org` | `NUMERIC(12,2)` | NOT NULL | Balance origen antes |
| `newbalance_orig` | `NUMERIC(12,2)` | NOT NULL | Balance origen después |
| `oldbalance_dest` | `NUMERIC(12,2)` | NOT NULL | Balance destino antes |
| `newbalance_dest` | `NUMERIC(12,2)` | NOT NULL | Balance destino después |
| `ip_country` | `VARCHAR(2)` | NOT NULL | Código ISO del país (ES, KH, US...) |
| `merchant_category` | `VARCHAR(50)` | NOT NULL | crypto, electronics, groceries... |
| `fraud_probability` | `NUMERIC(5,4)` | NOT NULL, BETWEEN 0 AND 1 | Score del modelo |
| `risk_level` | `VARCHAR(10)` | NOT NULL | low / medium / high |
| `decision` | `VARCHAR(10)` | NOT NULL | allow / review / block |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, DEFAULT NOW() | Cuándo se procesó |

**Índices recomendados:**
- `CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);` (para consultas por rango temporal)
- `CREATE INDEX idx_transactions_decision ON transactions(decision);` (para filtrar por decisión)

### 4.3. Tabla `fraud_queue`

Guarda **solo los casos pendientes de revisión** (decisión = `review`). Es la bandeja de entrada del analista. Cuando el analista cierra un caso vía `POST /fraud/feedback`, el registro se borra de aquí (pero la transacción sigue en `transactions`).

| Columna | Tipo | Constraints | Descripción |
|---|---|---|---|
| `id` | `SERIAL` | PRIMARY KEY | Auto-incremental |
| `transaction_id` | `VARCHAR(50)` | FOREIGN KEY → transactions, UNIQUE | Transacción referenciada |
| `added_to_queue_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, DEFAULT NOW() | Cuándo entró en cola |
| `analyst_id` | `VARCHAR(50)` | NULL | Analista que la ha tomado (NULL si nadie aún) |

**Diseño elegido: referencia con FK + JOIN.** Evita duplicación de datos. Para mostrar la cola al analista, se hace JOIN con `transactions`. El coste del JOIN es despreciable con los volúmenes esperados (cientos o miles de transacciones, no millones).

### 4.4. Tabla `analyst_feedback`

Guarda el feedback de los analistas. Es **oro para Ronda 2**: son los casos etiquetados por humanos que sirven para reentrenar el modelo cuando el adversario se adapte.

| Columna | Tipo | Constraints | Descripción |
|---|---|---|---|
| `case_id` | `VARCHAR(20)` | PRIMARY KEY | Identificador `case_xxxxxxxx` |
| `transaction_id` | `VARCHAR(50)` | FOREIGN KEY → transactions | Transacción revisada |
| `analyst_decision` | `VARCHAR(20)` | NOT NULL | fraud / not_fraud / uncertain |
| `analyst_notes` | `TEXT` | NULL | Notas libres |
| `analyst_id` | `VARCHAR(50)` | NOT NULL | Quién revisó |
| `closed_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, DEFAULT NOW() | Cuándo se cerró |

### 4.5. Sobre datos personales (GDPR)

⚠️ **Comprobado:** ninguna tabla contiene PII (Personally Identifiable Information): no hay nombres, emails, IBANs, ni `user_id` real. Solo IDs sintéticos del dataset de fraude.

Si en Ronda 2 se decide añadir campos identificativos, **es responsabilidad de Ciberseguridad** definir:

- Cifrado en reposo (RDS lo ofrece nativo vía AWS KMS).
- Política de retención.
- Cifrado en tránsito (SSL/TLS obligatorio en la conexión).
- Auditoría de accesos (CloudTrail).

---

## 5. Prerrequisitos antes de tocar AWS

### 5.1. Coordinación con otras verticales (CRÍTICO)

Antes de levantar RDS, hay que validar con:

1. **Ciberseguridad (Red Team):** la decisión de usar RDS toca de lleno sus puntos del PDF (*"Diseño de infraestructura segura y escalable"*, *"Gestión y protección de datos: backup, retención"*). Necesitan:
   - Validar la configuración de security groups.
   - Definir la estrategia de backups (período de retención).
   - Aprobar las credenciales y su rotación.
   - Decidir si la base de datos será pública (NO recomendado) o solo accesible desde la VPC.

2. **Full Stack:** confirmar que no están montando su propia base de datos por separado. Si fuera el caso, hay que unificar — duplicar bases es un anti-patrón.

3. **Mentor (Sergio Fernández):** validación general de la decisión arquitectónica.

**Acción pendiente:** convocar reunión rápida (15 min) con representantes de las tres verticales antes de ejecutar el Paso 1 de este documento.

### 5.2. Cuenta AWS y costes

⚠️ Verificar antes de empezar:

- **¿De quién es la cuenta AWS?** Identificar al titular para que sea consciente de cualquier cargo.
- **¿Está la cuenta dentro del free tier (primeros 12 meses)?** Si sí, `db.t3.micro` con 20 GB es gratis. Si no, el coste estimado es de ~15 USD/mes en la región Madrid.
- **Configurar AWS Budgets** con una alerta a 5 USD para evitar sorpresas.

### 5.3. Herramientas locales

Cada miembro del equipo que vaya a interactuar con RDS necesita:

- AWS CLI v2 instalada y configurada (`aws configure`).
- `psql` (cliente PostgreSQL) para pruebas de conexión.
- Permisos IAM adecuados (al menos `AmazonRDSFullAccess` y `AmazonEC2FullAccess` durante el desarrollo; reducir después).

---

## 6. Plan de implementación

El plan se divide en dos fases:

- **Fase A:** Postgres en contenedor local (días 1-3). Permite desarrollar y probar sin depender de AWS.
- **Fase B:** Migración a RDS en EC2 (días 4-5). Solo cambia la `DATABASE_URL`.

### Fase A — Postgres en contenedor local

#### Paso A.1 — Añadir Postgres al `docker-compose.yml`

Crear o modificar `docker-compose.yml` en la raíz del proyecto:

```yaml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://sentinel:sentinel_dev_pwd@db:5432/sentinel_db
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: sentinel
      POSTGRES_PASSWORD: sentinel_dev_pwd
      POSTGRES_DB: sentinel_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sentinel -d sentinel_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

> ⚠️ **La contraseña `sentinel_dev_pwd` es solo para desarrollo local.** Para RDS se usará una contraseña fuerte gestionada vía AWS Secrets Manager o variable de entorno en EC2.

#### Paso A.2 — Añadir dependencias Python

En `requirements-api.txt`:

```
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.9
alembic>=1.13.0
```

`alembic` es opcional pero recomendado para gestionar migraciones del esquema sin destruir datos.

#### Paso A.3 — Crear `src/database.py`

Módulo nuevo. Centraliza la conexión y la sesión de SQLAlchemy. La filosofía: **un único punto de configuración**, leído de `DATABASE_URL`.

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sentinel:sentinel_dev_pwd@localhost:5432/sentinel_db"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_session():
    """Generator para usar con FastAPI Depends."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

#### Paso A.4 — Definir los modelos ORM en `src/models.py`

Archivo nuevo con las tres tablas usando SQLAlchemy:

```python
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from src.database import Base


class TransactionDB(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(50), primary_key=True)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(20), nullable=False)
    oldbalance_org = Column(Numeric(12, 2), nullable=False)
    newbalance_orig = Column(Numeric(12, 2), nullable=False)
    oldbalance_dest = Column(Numeric(12, 2), nullable=False)
    newbalance_dest = Column(Numeric(12, 2), nullable=False)
    ip_country = Column(String(2), nullable=False)
    merchant_category = Column(String(50), nullable=False)
    fraud_probability = Column(Numeric(5, 4), nullable=False)
    risk_level = Column(String(10), nullable=False)
    decision = Column(String(10), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class FraudQueueDB(Base):
    __tablename__ = "fraud_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(
        String(50),
        ForeignKey("transactions.transaction_id"),
        unique=True,
        nullable=False,
    )
    added_to_queue_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    analyst_id = Column(String(50), nullable=True)

    transaction = relationship("TransactionDB")


class AnalystFeedbackDB(Base):
    __tablename__ = "analyst_feedback"

    case_id = Column(String(20), primary_key=True)
    transaction_id = Column(
        String(50),
        ForeignKey("transactions.transaction_id"),
        nullable=False,
    )
    analyst_decision = Column(String(20), nullable=False)
    analyst_notes = Column(String, nullable=True)
    analyst_id = Column(String(50), nullable=False)
    closed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

#### Paso A.5 — Refactorizar `src/storage.py`

**Clave de este paso:** mantener la misma firma de funciones que el código actual (`add_to_queue`, `get_queue`, `store_feedback`, etc.). Si la interfaz no cambia, `fraud.py` no necesita ningún cambio.

Ejemplo de antes/después de una función:

```python
# ANTES (volátil)
_pending_transactions = {}

def add_to_queue(item):
    _pending_transactions[item.transaction_id] = item

# DESPUÉS (persistente)
from src.database import SessionLocal
from src.models import FraudQueueDB

def add_to_queue(item):
    session = SessionLocal()
    try:
        record = FraudQueueDB(transaction_id=item.transaction_id)
        session.add(record)
        session.commit()
    finally:
        session.close()
```

> ⚠️ La sesión de SQLAlchemy se abre y cierra en cada llamada. Para optimizar, en una iteración posterior se puede usar el patrón de inyección de dependencias de FastAPI (`Depends(get_session)`).

#### Paso A.6 — Script de inicialización del esquema

Crear `scripts/init_db.py`:

```python
from src.database import engine, Base
from src.models import TransactionDB, FraudQueueDB, AnalystFeedbackDB

print("Creando tablas...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas.")
```

Se ejecuta una sola vez:

```bash
docker compose exec api python scripts/init_db.py
```

#### Paso A.7 — Pruebas locales

1. `docker compose up -d` — levantar API + Postgres.
2. `docker compose exec api python scripts/init_db.py` — crear tablas.
3. Llamadas a `POST /fraud/decide` desde Postman con varias transacciones.
4. `GET /fraud/queue` — verificar que los casos de `review` están persistidos.
5. `docker compose restart api` — **prueba clave**: reiniciar la API.
6. `GET /fraud/queue` de nuevo — los datos siguen ahí. ✅

### Fase B — Migración a RDS en EC2 (Madrid)

#### Paso B.1 — Crear instancia RDS desde la consola AWS

1. Entrar en la consola AWS → región **`Europe (Spain)` / `eu-south-2`**.
2. Servicio **RDS** → "Create database".
3. Configuración:
   - **Engine:** PostgreSQL
   - **Version:** 16.x (la más reciente disponible)
   - **Template:** Free tier (si la cuenta es elegible) o Dev/Test
   - **DB instance identifier:** `sentinel-db`
   - **Master username:** `sentinel`
   - **Master password:** generada (mínimo 16 caracteres, guardar en gestor de contraseñas)
   - **Instance class:** `db.t3.micro`
   - **Storage:** 20 GB gp3, sin autoscaling
   - **VPC:** la misma que la EC2 de la API
   - **Public access:** **NO** ⚠️
   - **VPC security group:** crear nuevo, llamarlo `sentinel-db-sg`
   - **Initial database name:** `sentinel_db`
   - **Backup retention:** 7 días
   - **Encryption:** activada (AWS KMS, clave por defecto)
   - **Deletion protection:** activada

> ⚠️ **Algunos nombres de pantalla o campos pueden variar** según actualizaciones de la consola AWS. Si no encuentras alguna opción exactamente como aparece aquí, busca el nombre similar — el concepto es el mismo. Referencia oficial: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_GettingStarted.CreatingConnecting.PostgreSQL.html

#### Paso B.2 — Configurar el security group de RDS

El RDS solo debe aceptar conexiones **desde el security group de la EC2**, no desde Internet.

1. Ir a EC2 → Security Groups → `sentinel-db-sg`.
2. Inbound rules → Add rule:
   - **Type:** PostgreSQL
   - **Port:** 5432
   - **Source:** Custom → el security group de la EC2 de la API (algo como `sg-xxxxxx`).
3. Guardar.

Esto significa: solo la EC2 puede hablar con RDS. Nadie más, ni siquiera desde tu portátil directamente. Cumple con el OWASP Top 10 (A05 Security Misconfiguration).

> Para conectarse desde un portátil para debugging, usar un **bastion host** o **AWS Session Manager**, nunca abrir el puerto 5432 al mundo.

#### Paso B.3 — Probar conexión desde la EC2

Conectarse a la EC2 por SSH:

```bash
ssh -i clave.pem ec2-user@<IP_PUBLICA_EC2>
```

Instalar el cliente:

```bash
sudo dnf install -y postgresql16
```

Conectar a RDS (el endpoint aparece en la consola de RDS, algo como `sentinel-db.xxxxx.eu-south-2.rds.amazonaws.com`):

```bash
psql -h sentinel-db.xxxxx.eu-south-2.rds.amazonaws.com \
     -U sentinel \
     -d sentinel_db
```

Te pide la contraseña. Si entra y aparece el prompt `sentinel_db=>`, la conectividad funciona. ✅

#### Paso B.4 — Configurar `DATABASE_URL` en la EC2

En la EC2, editar el archivo `.env` (no commitearlo en git):

```bash
DATABASE_URL=postgresql://sentinel:<PASSWORD>@sentinel-db.xxxxx.eu-south-2.rds.amazonaws.com:5432/sentinel_db
```

En `docker-compose.yml` de la EC2, **eliminar el servicio `db`** (ya no se usa Postgres local) y dejar solo el servicio `api` con la nueva `DATABASE_URL`.

#### Paso B.5 — Inicializar el esquema en RDS

Una sola vez:

```bash
docker compose exec api python scripts/init_db.py
```

Las tablas se crean en RDS.

#### Paso B.6 — Smoke test en producción

1. `curl http://<IP_PUBLICA_EC2>:8000/health` — la API responde.
2. `curl http://<IP_PUBLICA_EC2>:8000/ready` — el modelo está cargado.
3. `POST /fraud/decide` con una transacción de prueba.
4. Verificar en RDS que el registro existe:

```sql
SELECT * FROM transactions ORDER BY created_at DESC LIMIT 5;
```

5. `docker compose restart api` — reiniciar.
6. `GET /fraud/queue` — los datos persisten. ✅

---

## 7. Seguridad

Sección revisada con Ciberseguridad (pendiente). Cubre el OWASP Top 10 aplicable:

| Riesgo OWASP | Mitigación |
|---|---|
| **A01 — Broken Access Control** | RDS no expuesto públicamente. Solo accesible vía security group de EC2. |
| **A02 — Cryptographic Failures** | Cifrado en reposo (AWS KMS). Cifrado en tránsito (SSL/TLS forzado). Contraseña fuera del código (env var + Secrets Manager en futuro). |
| **A03 — Injection** | SQLAlchemy ORM con consultas parametrizadas. Pydantic valida los inputs en la capa API antes de llegar a la BBDD. |
| **A05 — Security Misconfiguration** | Public access desactivado. Deletion protection activada. Backups automáticos 7 días. |
| **A07 — Identification and Authentication Failures** | Contraseña de master fuerte (16+ caracteres). Rotación cada 90 días (pendiente de automatizar). |
| **A09 — Security Logging and Monitoring Failures** | CloudWatch Logs activado en RDS (pendiente). CloudTrail para auditoría de accesos a nivel API de AWS. |

---

## 8. Backups y recuperación

- **Backups automáticos:** RDS toma snapshots diarios. Retención: 7 días.
- **Snapshots manuales:** se pueden hacer antes de cambios grandes (despliegues mayores, migraciones de esquema).
- **Recuperación point-in-time:** RDS permite restaurar a cualquier segundo de los últimos 7 días.
- **Coste:** los backups dentro del tamaño de almacenamiento provisionado (20 GB) son gratuitos.

---

## 9. Plan de rollback

Si algo va mal en la Fase B y hay que volver al estado anterior:

1. En la EC2, revertir `docker-compose.yml` para usar Postgres en contenedor (Fase A).
2. Cambiar `DATABASE_URL` para apuntar a `db:5432` (servicio local).
3. `docker compose up -d`.
4. Reinicializar el esquema con `init_db.py`.

⚠️ **Limitación conocida:** los datos generados en RDS no se migran automáticamente al contenedor local. Si esto es crítico, hacer `pg_dump` antes del rollback:

```bash
pg_dump -h sentinel-db.xxxxx.eu-south-2.rds.amazonaws.com \
        -U sentinel \
        -d sentinel_db \
        > backup_$(date +%Y%m%d).sql
```

---

## 10. Cómo defenderlo ante el jurado

Argumentos clave para la presentación final (15 min):

**Si preguntan "¿por qué RDS y no SQLite?":**
> "RDS es el estándar de la industria fintech, ofrece backups automáticos, cifrado en reposo y alta disponibilidad sin que el equipo tenga que gestionarlo. SQLite no escalaría más allá de un MVP local."

**Si preguntan "¿por qué no usasteis Postgres en contenedor directamente en EC2?":**
> "Lo hicimos durante el desarrollo, en local. Para producción decidimos RDS porque cumple con los puntos 3 y 4 de los requisitos de Ciberseguridad: infraestructura segura, escalable, y gestión profesional de datos. Y el código no cambió ni una línea — solo la cadena de conexión."

**Si preguntan "¿qué pasa si NovaPay crece a millones de transacciones?":**
> "El diseño actual escala vertical hasta `db.r6g.16xlarge` sin tocar código. Para escalado horizontal habría que añadir read replicas, que RDS soporta nativamente con un solo botón."

**Si preguntan "¿qué pasa si AWS cae?":**
> "Para producción real, activaríamos Multi-AZ en RDS y backups multi-región. En este reto formativo no estaba justificado por el coste, pero la arquitectura lo soporta."

---

## 11. Deuda técnica conocida

Cosas que **no** están hechas aún y que se documentan para Ronda 2 o futuro:

| Deuda | Prioridad | Notas |
|---|---|---|
| Contraseña de RDS en AWS Secrets Manager | Media | Ahora está en `.env` de la EC2. Mejorable. |
| Read replicas para consultas pesadas (`/queue` cuando crezca) | Baja | No justificado en Ronda 1. |
| Particionado de `transactions` por mes | Baja | Solo necesario a partir de cientos de miles de registros. |
| Multi-AZ para alta disponibilidad | Baja | Coste no justificable en proyecto formativo. |
| Pool de conexiones explícito (`pool_size`, `max_overflow`) | Media | Ahora se usa el default de SQLAlchemy. |
| Migraciones gestionadas con Alembic | Media | Actualmente `init_db.py` recrea tablas; no soporta cambios incrementales. |
| Tests automatizados de la capa de persistencia | Alta | Solo hay smoke tests manuales con Postman. |

---

## 12. Glosario rápido

- **RDS** — Relational Database Service. Servicio de AWS que gestiona bases de datos relacionales.
- **EC2** — Elastic Compute Cloud. Máquinas virtuales de AWS.
- **VPC** — Virtual Private Cloud. Red privada virtual donde corren los recursos.
- **Security Group** — firewall a nivel de instancia.
- **ORM** — Object-Relational Mapping. Capa que traduce entre objetos Python y tablas SQL.
- **PII** — Personally Identifiable Information. Datos personales sujetos a regulación (GDPR).
- **Snapshot** — copia puntual de la base de datos.

---

## 13. Referencias

- AWS RDS PostgreSQL — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html
- SQLAlchemy 2.0 — https://docs.sqlalchemy.org/en/20/
- PDF del reto Desafío de Tripulaciones — Cívica, mayo 2026
- Report técnico interno — Juan Ramón Torres, `notebooks/22_05_ReportAPI.ipynb` (punto 2: persistencia)
