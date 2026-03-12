======================================================================
KEYCLOAK 26 MIGRATION GUIDE: BCRYPT SUPPORT (PHP/LARAVEL)
======================================================================
Status: Environment Validated (Keycloak 26.0.5)
Provider: keycloak-bcrypt-1.7.0.jar
Updated: 2026-03-12
======================================================================

1. DIRECTORY STRUCTURE
----------------------------------------------------------------------
.
├── docker-compose.yml
├── providers/
│   └── keycloak-bcrypt-1.7.0.jar  # Custom SPI JAR
└── data/                          # Postgres persistence volume

2. DOCKER-COMPOSE.YML
----------------------------------------------------------------------
services:
  keycloak_db:
    image: postgres:15
    container_name: keycloak_db
    volumes:
      - ./data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: password

  keycloak:
    image: quay.io/keycloak/keycloak:26.0.5
    container_name: keycloak_migration
    command: start-dev --import-realm
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://keycloak_db:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: password
      KC_HOSTNAME: localhost
      KC_BOOTSTRAP_ADMIN_USERNAME: admin
      KC_BOOTSTRAP_ADMIN_PASSWORD: admin
    volumes:
      - ./providers:/opt/keycloak/providers
    ports:
      - "8080:8080"
    depends_on:
      - keycloak_db

3. ACTIVATION & BUILD (QUARKUS)
----------------------------------------------------------------------
Keycloak 26 requires a build step to register custom providers:

# 1. Trigger the build
docker compose exec keycloak /opt/keycloak/bin/kc.sh build

# 2. Restart the stack
docker compose restart keycloak

# 3. Verification
Go to: Server Info -> Providers -> Password Hashing -> Confirm 'bcrypt' is listed.

4. REALM PASSWORD POLICY
----------------------------------------------------------------------
You MUST enable the policy in the UI:
1. Authentication -> Policies -> Password Policy.
2. Add Policy -> Select 'BCrypt'.
3. Click Save.

5. EXPERIMENTAL DATA STANDARDS & SQL
----------------------------------------------------------------------
*** CAUTION: EXPERIMENTAL STATUS - REQUIRES FIELD TESTING ***
Direct SQL updates bypass Keycloak's internal logic and may cause 
cache desynchronization with Infinispan.

Key Findings:
- Entity version MUST be set to 4 for Keycloak 26.
- Java providers require the $2a$ prefix (PHP $2y$ will fail).
- hashIterations must be -1 to delegate cost to the hash string.

# SQL Experimental Fix Script:
UPDATE credential 
SET 
    credential_data = '{"hashIterations":-1,"algorithm":"bcrypt","additionalParameters":{}}',
    secret_data = REPLACE(secret_data, '"$2y$', '"$2a$'), 
    version = 4,   
    priority = 10  
WHERE 
    type = 'password' 
    AND (credential_data LIKE '%bcrypt%' OR secret_data LIKE '%$2y$%');

6. JSON PARTIAL IMPORT TEMPLATE
----------------------------------------------------------------------
{
  "username": "migrated_user",
  "enabled": true,
  "credentials": [
    {
      "type": "password",
      "credentialData": "{\"hashIterations\":-1,\"algorithm\":\"bcrypt\",\"additionalParameters\":{}}",
      "secretData": "{\"value\":\"$2a$10$HASH_HERE\",\"salt\":\"\",\"additionalParameters\":{}}"
    }
  ]
}

7. TROUBLESHOOTING
----------------------------------------------------------------------
- Monitor Logs: docker logs -f keycloak_migration
- Clear Cache: If DB updates don't show up, run:
  docker compose up -d --force-recreate
- 72 Char Limit: BCrypt ignores characters beyond the 72nd position.
======================================================================
