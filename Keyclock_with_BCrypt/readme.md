# KEYCLOAK 26 ENVIRONMENT GUIDE: BCRYPT SUPPORT (PHP/LARAVEL)

**Status:** Environment Validated (Keycloak 26.0.5)\
**Provider:** keycloak-bcrypt-1.7.0.jar\
**Updated:** 2026-03-12

------------------------------------------------------------------------

## 1. Directory Structure

    .
    ├── docker-compose.yml
    ├── providers/
    │   └── keycloak-bcrypt-1.7.0.jar  # Custom SPI JAR
    └── data/                          # Postgres persistence volume

------------------------------------------------------------------------

## 2. docker-compose.yml (Validated YAML)

``` yaml
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
```

------------------------------------------------------------------------

## 3. Activation 

To configure Keycloak to use the BCrypt JAR file:

Navegate to:

    Authentication -> Policies -> Password Policy.

    Add Policy -> Selecione 'BCrypt'

    Save.

<img width="1346" height="754" alt="image" src="https://github.com/user-attachments/assets/47c9d2b6-1436-450d-b985-1fe78f27fd78" />


Verification

Navigate to:

    Server Info -> Providers -> Password Hashing

Confirm the presence of:

    bcrypt


<img width="813" height="454" alt="image" src="https://github.com/user-attachments/assets/9c2daa94-6dd3-41fd-90f2-893ba77fe79e" />

------------------------------------------------------------------------

## 4. Experimental Data Standards (Under Test)

⚠️⚠️⚠️⚠️⚠️⚠️⚠️ **Caution:** Requires field testing.\
Direct SQL updates bypass Keycloak internal validation logic.⚠️⚠️⚠️⚠️⚠️⚠️

# Keycloak BCrypt Migration Guide (PHP to Keycloak)

This guide provides the necessary configurations and scripts to enable **Keycloak** to validate password hashes migrated from **PHP** (which typically use the `$2y$` prefix).

## 💡 Migration Logic

To ensure compatibility between PHP's BCrypt and Keycloak's Java-based implementation, the following parameters must be met:

*   **Hash Iterations**: Set to `-1` (this forces Keycloak to use the cost factor already defined in the hash string).
*   **Entity Version**: Set to `4`.
*   **Prefix Transformation**: PHP's `$2y$` prefix must be converted to `$2a$` to be recognized by the standard BCrypt library.

---

## 🛠 1. Bulk Update SQL (PHP to Keycloak)

Use the following SQL script to update existing credentials directly in your Keycloak database. This is the fastest way to migrate a large volume of users.

```sql
-- Update BCrypt credentials to match Keycloak's requirements
UPDATE credential 
SET 
    credential_data = '{"hashIterations":-1,"algorithm":"bcrypt","additionalParameters":{}}',
    -- Replaces PHP variant ($2y$) with standard variant ($2a$)
    secret_data = REPLACE(secret_data, '"$2y$', '"$2a$'),
    version = 4
WHERE credential_data LIKE '%bcrypt%';
```
```
{
  "username": "migration_test_user",
  "enabled": true,
  "credentials": [
    {
      "type": "password",
      "credentialData": "{\"hashIterations\":-1,\"algorithm\":\"bcrypt\",\"additionalParameters\":{}}",
      "secretData": "{\"value\":\"$2a$10$HASH_GOES_HERE\",\"salt\":\"\",\"additionalParameters\":{}}"
    }
  ]
}

```

## 🛠  2. Below is an example of a user import file containing password credentials using the BCrypt algorithm:

```
[
  {
    "username": "user_bcrypt",
    "enabled": true,
    "credentials": [
      {
        "type": "password",
        "algorithm": "bcrypt",
        "hashedSaltedValue": "$2a$10$8.UnVuG9HHgffUDAlk8q2Ou5JL2n17ba6WqEnwfS79Cq7yzrtauW6"
      }
    ]
  }
]
```



Important Note: 
Ensure you have the BCrypt Password Hashing Provider JAR file installed in your Keycloak deployment (usually in the providers/ or standalone/deployments/ directory) before attempting to authenticate users with these credentials.



