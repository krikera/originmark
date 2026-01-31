# OriginMark API Architecture

```mermaid
graph TB
    subgraph "OriginMark API Architecture"
        Client[Client Request] --> Auth{Authentication}
        Auth -->|Valid API Key| AuthUser[Authenticated User]
        Auth -->|No API Key| AnonUser[Anonymous User]
        
        AuthUser --> APIEndpoints
        AnonUser --> APIEndpoints
        
        subgraph APIEndpoints["API Endpoints"]
            SignEP["/sign<br/>Sign Content"]
            VerifyEP["/verify<br/>Verify Signature"]
            BadgeEP["/badge<br/>Generate Badge"]
            SigEP["/signatures/{id}<br/>Get Signature"]
            UserEP["/users/{id}/signatures<br/>User Signatures"]
            AuthMgmt["Auth Management<br/>/auth/*"]
            WebhookMgmt["Webhook Management<br/>/webhooks/*"]
        end
        
        APIEndpoints --> Business{Business Logic}
        
        subgraph Business["Core Operations"]
            KeyGen[Key Generation<br/>Ed25519]
            Hash[Content Hashing<br/>SHA-256]
            Sign[Digital Signing<br/>NaCl]
            Verify[Signature Verification]
        end
        
        Business --> Database[(SQLite Database)]
        
        subgraph Database
            Users[Users Table]
            APIKeys[API Keys Table]
            Signatures[Signatures Table]
        end
        
        Business --> Webhooks[Webhook System]
        
        subgraph Webhooks["Webhook Notifications"]
            Slack[Slack Integration]
            Discord[Discord Integration]
            Events["Events:<br/>• signature.created<br/>• signature.verified<br/>• signature.failed<br/>• batch.completed"]
        end
        
        SignEP --> WebhookTrigger[Trigger Webhook]
        WebhookTrigger --> Webhooks
        
        subgraph Security["Security Features"]
            RateLimit[Rate Limiting]
            KeyRotation[Key Rotation]
            Encryption[Content Encryption]
        end
        
        AuthUser --> Security
    end
    
    style Auth fill:#e1f5fe
    style Business fill:#f3e5f5
    style Database fill:#e8f5e8
    style Webhooks fill:#fff3e0
    style Security fill:#ffebee
```

## Description
This diagram shows the complete FastAPI backend architecture including authentication, core endpoints, business logic, database schema, webhook system, and security features. 