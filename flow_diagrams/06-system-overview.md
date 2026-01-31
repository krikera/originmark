# OriginMark System Overview

```mermaid
graph TB
    subgraph "OriginMark System Overview"
        
        subgraph UserLayer["User Interfaces"]
            WebDashboard["Web Dashboard<br/>Next.js 15 + TailwindCSS<br/>Framer Motion"]
            BrowserExt["Browser Extension<br/>Chrome MV3"]
            CommandLine["Command Line<br/>Python CLI"]
            IDEIntegration["IDE Integration<br/>VS Code, etc."]
        end
        
        subgraph SDKLayer["SDK Layer"]
            TypeScriptSDK["TypeScript SDK<br/>libsodium + ES2022"]
            Web3SDK["Web3 SDK<br/>ethers.js v6 + IPFS"]
            PythonSDK["Python CLI<br/>PyNaCl + Rich"]
        end
        
        subgraph APILayer["API Service Layer"]
            FastAPIServer["FastAPI Server<br/>Python + SQLAlchemy"]
            Authentication["Bearer Token Auth<br/>API Key Management"]
            RateLimiting["Rate Limiting<br/>Per-user Quotas"]
        end
        
        subgraph CryptoLayer["Cryptographic Layer"]
            Ed25519Keys["Ed25519 Key Pairs<br/>Public/Private Keys"]
            DigitalSigning["Digital Signatures<br/>NaCl Implementation"]
            ContentHashing["SHA-256 Hashing<br/>Content Integrity"]
            KeyRotation["Key Rotation<br/>Security Management"]
        end
        
        subgraph BlockchainLayer["Blockchain Layer"]
            SmartContract["OriginMarkRegistry<br/>Solidity Contract"]
            MerkleProofs["Merkle Tree Proofs<br/>Batch Verification"]
            IPFSStorage["IPFS Storage<br/>Decentralized Data"]
        end
        
        subgraph StorageLayer["Storage Layer"]
            SQLiteDB[("SQLite Database<br/>Users, Keys, Signatures")]
            SidecarFiles["Sidecar JSON Files<br/>Portable Signatures"]
            LocalStorage["Browser Local Storage<br/>Settings & Cache"]
            FileSystem["File System<br/>Local Operations"]
        end
        
        subgraph IntegrationLayer["Integration Layer"]
            GitHubActions["GitHub Actions<br/>CI/CD Workflows"]
            WebhookSystem["Webhook System<br/>Slack, Discord"]
            PreCommitHooks["Pre-commit Hooks<br/>Local Git Integration"]
            C2PAExport["C2PA Export<br/>Industry Standard"]
        end
        
        subgraph ExternalServices["External Services"]
            SlackAPI["Slack API<br/>Team Notifications"]
            DiscordAPI["Discord API<br/>Community Alerts"]
            GitHubAPI["GitHub API<br/>Repository Integration"]
            EthereumRPC["Ethereum RPC<br/>Blockchain Access"]
        end
        
        %% User Layer Connections
        WebDashboard --> TypeScriptSDK
        WebDashboard --> FastAPIServer
        BrowserExt --> FastAPIServer
        CommandLine --> PythonSDK
        IDEIntegration --> PythonSDK
        
        %% SDK Layer Connections
        TypeScriptSDK --> FastAPIServer
        TypeScriptSDK --> CryptoLayer
        Web3SDK --> BlockchainLayer
        PythonSDK --> FastAPIServer
        PythonSDK --> CryptoLayer
        
        %% API Layer Connections
        FastAPIServer --> Authentication
        FastAPIServer --> RateLimiting
        FastAPIServer --> CryptoLayer
        FastAPIServer --> StorageLayer
        FastAPIServer --> WebhookSystem
        
        %% Blockchain Connections
        BlockchainLayer --> SmartContract
        BlockchainLayer --> IPFSStorage
        BlockchainLayer --> EthereumRPC
        
        %% Crypto Layer Connections
        CryptoLayer --> SidecarFiles
        CryptoLayer --> SQLiteDB
        
        %% Storage Layer Connections
        SQLiteDB --> Authentication
        SidecarFiles --> FileSystem
        LocalStorage --> BrowserExt
        
        %% Integration Layer Connections
        GitHubActions --> PythonSDK
        GitHubActions --> FastAPIServer
        WebhookSystem --> SlackAPI
        WebhookSystem --> DiscordAPI
        PreCommitHooks --> PythonSDK
        
        %% Data Flow Indicators
        UserLayer -.->|File Upload| APILayer
        APILayer -.->|Signature Response| UserLayer
        CryptoLayer -.->|Verification| IntegrationLayer
        IntegrationLayer -.->|Notifications| ExternalServices
        
        %% Security Boundaries
        subgraph SecurityBoundary["Security Perimeter"]
            CryptoLayer
            Authentication
            KeyRotation
        end
        
        %% Local vs Remote Operations
        subgraph LocalOps["Local Operations"]
            SidecarFiles
            LocalStorage
            FileSystem
            PreCommitHooks
        end
        
        subgraph RemoteOps["Remote Operations"]
            FastAPIServer
            SQLiteDB
            WebhookSystem
            ExternalServices
        end
        
        subgraph ModernStack["Modern Technology Stack"]
            NextJS15["Next.js 15 + Turbopack"]
            React18["React 18"]
            FramerMotion["Framer Motion"]
            Python310["Python 3.10+"]
            TypeScript5["TypeScript 5.x"]
            Node20["Node.js 20+ LTS"]
        end
    end
    
    style UserLayer fill:#e8f5e8
    style SDKLayer fill:#fff3e0
    style APILayer fill:#e3f2fd
    style CryptoLayer fill:#ffebee
    style BlockchainLayer fill:#f3e5f5
    style StorageLayer fill:#f1f8e9
    style IntegrationLayer fill:#fce4ec
    style ExternalServices fill:#e8eaf6
    style SecurityBoundary fill:#fff3e0,stroke:#ff9800,stroke-width:3px
    style LocalOps fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    style RemoteOps fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style ModernStack fill:#f5f5f5,stroke:#9e9e9e,stroke-width:2px
```

## Description

This provides a high-level view of all OriginMark components showing:

### Modern Technology Stack
- **Next.js 15** with Turbopack for web dashboard
- **React 18** with modern hooks
- **Framer Motion** for animations
- **TypeScript 5.x** with strict mode
- **Python 3.10+** with modern type hints
- **Node.js 20+ LTS** runtime

### User Interfaces
- Web Dashboard (Next.js 15 + TailwindCSS)
- Browser Extension (Chrome MV3)
- Command Line (Python CLI)
- IDE Integration

### SDK Layer
- TypeScript SDK (ES2022, libsodium)
- Web3 SDK (ethers.js v6, IPFS)
- Python CLI (PyNaCl, Rich)

### Blockchain Integration
- Smart contract for on-chain registration
- Merkle tree proofs for batch verification
- IPFS for decentralized storage

### Security Features
- Ed25519 digital signatures
- Content hashing (SHA-256)
- Key rotation management
- Rate limiting and authentication