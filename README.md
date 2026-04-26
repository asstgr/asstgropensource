# asstgr

---

 **Technologies Used**
This project is built on a modern stack focused on backend APIs and real-time capabilities:

* Django — Main framework for server-side logic and project structure
* Django REST Framework (DRF) — Building robust and secure REST APIs
* JWT (SimpleJWT) — Token-based authentication (access + refresh)
* PostgreSQL — Relational database
* Daphne (ASGI) — Support for asynchronous communication (real-time)
* Cloudinary — Media file management and storage
* django-storages — Integration with external storage services
* Python-dotenv — Environment variable management
* Custom User Model — Custom authentication system
* Custom Throttling — API rate limiting

**Project Description**
Asstgr is a platform that allows users to create, configure, and use APIs.

 **Key Features**

* 🔧 Create custom APIs through an interface
* 🔗 Add dynamic endpoints
* ⚙️ Configure HTTP methods (GET, POST, etc.)
* 🧩 Advanced parameter management (query, path, body)
* 🔐 Secure API key and header management
* 🚀 Execute API requests directly from the platform
* 📊 Quota system and rate limiting (burst + daily usage)
* 🔑 Authentication via API Key or JWT
* 🔄 OAuth 2.0 support
* 📡 Public API to automate all actions


**Software Objective**
The goal of Asstgr is to simplify API usage as much as possible:


**Security**

* Secure API key storage
* JWT-based authentication
* Token rotation
* Configurable rate limiting
* CSRF protection and Django middleware

**Architecture**
The project is structured into multiple apps:

* users — user management and authentication
* api_management — API creation and management
* api_public — public endpoints (external API)
* core — core logic

---