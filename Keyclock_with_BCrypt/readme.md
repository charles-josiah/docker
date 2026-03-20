![Status](https://img.shields.io/badge/status-experimental-yellow)
# 🚀 Keycloak 26: BCrypt Environment (Python/PHP/Laravel)

> **Status:** Ambiente Validado (Keycloak 26.0.5)  
> **Provider:** `keycloak-bcrypt-1.7.0.jar`  
> **Data de Atualização:** 13 de Março de 2026  
> **Autor:** Charles Josiah Rusch Alandt

---
> ⚠️ **IMPORTANT DISCLAIMER**
>
> This environment has been developed **exclusively for testing, validation, and educational purposes**.
> It is **not intended for production use under any circumstances**.
> The configurations, versions, dependencies, and behaviors described herein **may change at any time without prior notice**, and no guarantees are made regarding stability, security, or future compatibility.
> Use of this material is entirely at your own risk. It is the user's responsibility to perform proper validation, security assessment, and adjustments before any production deployment.

---

## 📂 1. Recommended File Structure
To ensure proper functioning of volumes and the provider, organize the directory as follows:

```text
/docker
├── docker-compose.yml
├── providers/
│   └── keycloak-bcrypt-1.7.0.jar  # Download em: [github.com/leroyguillaume/keycloak-bcrypt](https://github.com/leroyguillaume/keycloak-bcrypt)
└── data/                          # Criado automaticamente (Persistência Postgres)

```

## 🚀 2. Environment Startup Guide

Follow these steps in the terminal to start Keycloak 26 with BCrypt support.

2.1. File Preparation

Make sure the provider JAR is in the correct folder before starting.

```bash
# Criar estrutura de pastas
mkdir docker 
cd docker 
mkdir -p providers data

# Copiar o JAR do BCrypt para a pasta de providers
# Substitua o caminho abaixo pelo local onde você baixou o JAR
cp ./keycloak-bcrypt-1.7.0.jar ./providers/

```

### 🐳 2.2. Docker Compose 


```yaml

cat docker-compose.yaml 

version: '3.8'

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
  
 ### 🐳 2.3. Start the Docker Stack
 
Start the containers in daemon mode (background).

```bash
  docker compose up -d
```
  
### 🐳 2.4. Validar logs

```bash
docker logs -f keycloak_migration
```

## 🔐 3. Enable BCrypt in Keycloak

To enable Keycloak to use the BCrypt provider:

- Authentication -> Policies -> Password Policy.
- Add Policy -> Escreva 'BCrypt' (notificação verde de sucesso) 
- Save.

<img width="2692" height="1508" alt="image" src="https://github.com/user-attachments/assets/abb8cb0d-0cab-4ab9-b080-314a53addd2c" />

### 3.1 Validation

To validate:

- Server Info -> Providers -> Password Hashing

Look for: `bcrypt`

<img width="2692" height="1508" alt="image" src="https://github.com/user-attachments/assets/6be59fec-3919-4686-96a5-55d03d832441" />
  
 ## 📑 4. Test Plan
 
> **Test Objective:** Validate BCrypt hash integrity, JSON compliance, and immediate access granting. The script uses Python 3 to simulate external credential generation, ensuring that Keycloak recognizes hashes created outside its native environment.
 
### 1. Import Generation Script
This script generates a JSON compatible with Partial Import, correcting prefixes and assigning required roles to avoid login errors.

```bash 
#!/bin/bash
# Salve como gerar_import.sh

read -p "Digite o Username: " USERNAME
read -s -p "Digite a Senha: " PASSWORD
echo ""

# Gera hash e converte prefixo $2b$ para $2a$ (Java Standard)
RAW_HASH=$(python3 -c "import crypt; print(crypt.crypt('$PASSWORD', crypt.mksalt(crypt.METHOD_BLOWFISH)))")
FINAL_HASH=$(echo $RAW_HASH | sed 's/^\$2b\$/\$2a\$/')

cat << 'EOF' > ${USERNAME}_import.json
{
  "users": [
    {
      "username": "REPLACE_USER",
      "enabled": true,
      "clientRoles": {
        "account": ["manage-account", "view-profile"]
      },
      "credentials": [
        {
          "type": "password",
          "userLabel": "Migration Hash",
          "credentialData": "{\"hashIterations\":-1,\"algorithm\":\"bcrypt\",\"additionalParameters\":{}}",
          "secretData": "{\"value\":\"REPLACE_HASH\",\"salt\":\"\",\"additionalParameters\":{}}",
          "version": 4
        }
      ]
    }
  ]
}
EOF

sed -i "s|REPLACE_USER|$USERNAME|g" ${USERNAME}_import.json
sed -i "s|REPLACE_HASH|$FINAL_HASH|g" ${USERNAME}_import.json

echo "Arquivo criado: ${USERNAME}_import.json"
```  
### 2. Import and Validation

Follow these steps to load the user and validate credential integrity:

1. **Access Admin Panel:**
   * Open **Admin Console**: `http://localhost:8080/admin/`
   * Ensure you are in the correct Realm (e.g., master).

2. **Data Load (Partial Import):**
   * In the top-right corner of the screen, click the **Action** button and select the **Partial Import** option.
   * Locate and upload the `${USERNAME}_import.json` file generated by the script.
   * In the resource selection screen, check the **Users** box and click the **Import** button.

<img width="1723" height="838" alt="image" src="https://github.com/user-attachments/assets/e17b8f28-4d13-4c5a-ad78-62c555c8ca16" />

3. **Imported Credential Inspection:**
   * Navigate to the side menu **Manage > Users** and locate the newly imported user.
   * Click on the username to open the details and select the **Credentials** tab.
   * You will find an item of type **Password**. Click the **Show Data** button.

<img width="1720" height="835" alt="image" src="https://github.com/user-attachments/assets/5b4f8d4e-795f-49a3-b890-34a974a0130e" />

4. **Cipher Audit (Critical Path):**
   * Verify that the displayed algorithm is **bcrypt**.
   * This check ensures that the hash conversion was correctly applied, allowing Keycloak to validate passwords originating from external systems.


### 3. Real Login Validation (Account Console)

To confirm that the hash has been accepted and that account permissions are operational, use the user self-service console:

1. **Clean Session:** Open an **Incognito or Private** tab in your browser to avoid cache conflicts with the Admin session.

2. **Access the Realm:** Use the profile management URL:
   > http://192.168.5.103:8080/realms/REALM_NAME/account/

   *Note: Replace **REALM_NAME** with the exact name displayed in the Admin panel selector (case-sensitive).*

3. **Authentication:** Enter the **Username** and **Password** defined in the generation script.

4. **Success Result**
   * The system should immediately redirect to the **"Personal Info"** page.

<img width="1029" height="531" alt="image" src="https://github.com/user-attachments/assets/e93f20ed-ac4e-43ea-b4cb-af75e0c647f6" />

   * The panel should load the user profile without displaying alerts such as *"Something went wrong"* or errors like *"Page not found"*.

---

### 📊 Tabela de Verificacao Tecnica
| Validador | Status | Detalhe Tecnico |
| :--- | :--- | :--- |
| **Prefixo** | ✅ OK | Hash convertido de $2y$ para $2a$. |
| **Iteracoes** | ✅ OK | Definido como `-1` no `credentialData`. |
| **Permissoes** | ✅ OK | Role `manage-account` atribuida no JSON. |
| **Cache** | ✅ OK | Paridade entre Banco de Dados e memoria RAM (Infinispan). |


---

## ⚠️ Final Note

This guide is provided for **experimental and educational purposes only**.

Any use in production environments should be preceded by:
- proper security review,
- controlled environment validation,
- compliance checks with applicable policies and regulations.

The author assumes no liability for any damages or issues arising from the misuse of this material.
  
  
