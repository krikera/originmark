# SDK Architecture

```mermaid
graph TB
    subgraph "SDK Architecture"
        
        subgraph TypeScriptSDK["TypeScript SDK (ts-sdk)"]
            TSEntry[OriginMarkSDK Class] --> TSMethods{Available Methods}
            
            TSMethods --> TSSignLocal["signContent<br/>Local Signing"]
            TSMethods --> TSVerifyLocal["verifyContent<br/>Local Verification"]
            TSMethods --> TSSignAPI["signContentAPI<br/>API Signing"]
            TSMethods --> TSVerifyAPI["verifyContentAPI<br/>API Verification"]
            TSMethods --> TSKeyGen["generateKeyPair<br/>Key Generation"]
            
            subgraph TSCore["Core TypeScript Components"]
                LibSodium["libsodium-wrappers<br/>Ed25519 Crypto"]
                Axios["Axios<br/>HTTP Client"]
                Utils["Utility Functions<br/>Hash, Encode, Validate"]
            end
            
            subgraph TSModern["Modern Features (ES2022+)"]
                NodeNext["NodeNext Module Resolution"]
                TypedArrays["Typed Arrays"]
                AsyncIterators["Async Iterators"]
                TopLevelAwait["Top-Level Await"]
            end
            
            TSSignLocal --> LibSodium
            TSVerifyLocal --> LibSodium
            TSSignAPI --> Axios
            TSVerifyAPI --> Axios
            TSKeyGen --> LibSodium
            
            subgraph TSUsage["Usage Scenarios"]
                WebApp["Web Applications"]
                NodeJS["Node.js 20+ LTS"]
                ReactApp["React 18+ Components"]
                ElectronApp["Electron Apps"]
            end
            
            TSEntry --> TSUsage
        end
        
        subgraph Web3SDK["Web3 SDK (web3-sdk)"]
            W3Entry[OriginMarkWeb3 Class] --> W3Methods{Web3 Features}
            
            W3Methods --> W3Register["registerOnChain<br/>Blockchain Registration"]
            W3Methods --> W3Merkle["createMerkleTree<br/>Batch Proofs"]
            W3Methods --> W3IPFS["storeIPFS<br/>Decentralized Storage"]
            W3Methods --> W3Verify["verifyOnChain<br/>Chain Verification"]
            
            subgraph W3Core["Web3 Components"]
                Ethers["ethers.js v6<br/>Blockchain Interaction"]
                IPFSClient["IPFS HTTP Client<br/>Decentralized Storage"]
                MerkleJS["merkletreejs<br/>Merkle Proofs"]
            end
            
            W3Register --> Ethers
            W3IPFS --> IPFSClient
            W3Merkle --> MerkleJS
        end
        
        subgraph PythonCLI["Python CLI (py-cli)"]
            CLIEntry["originmark command"] --> CLICommands{CLI Commands}
            
            CLICommands --> SignCmd["sign<br/>Sign Content"]
            CLICommands --> VerifyCmd["verify<br/>Verify Signature"]
            CLICommands --> GenKeysCmd["generate-keys<br/>Create Key Pair"]
            CLICommands --> ShowSigCmd["show-signature<br/>Display Signature Info"]
            
            subgraph CLICore["Core Python Components"]
                OriginMarkClass["OriginMarkClient Class<br/>Core Logic"]
                PyNaCl["PyNaCl<br/>Ed25519 Crypto"]
                Click["Click 8.x<br/>CLI Framework"]
                Rich["Rich 13.x<br/>Terminal UI"]
                Requests["Requests<br/>HTTP Client"]
            end
            
            subgraph CLIModern["Python 3.10+ Features"]
                TypeHints["Modern Type Hints<br/>str | None"]
                TZAware["Timezone-Aware datetime<br/>datetime.now(UTC)"]
                Pyproject["pyproject.toml<br/>Modern Packaging"]
                Ruff["Ruff Linter<br/>Fast Python Linting"]
            end
            
            SignCmd --> OriginMarkClass
            VerifyCmd --> OriginMarkClass
            GenKeysCmd --> OriginMarkClass
            ShowSigCmd --> OriginMarkClass
            
            OriginMarkClass --> PyNaCl
            CLICommands --> Click
            CLICommands --> Rich
            OriginMarkClass --> Requests
            
            subgraph CLIFeatures["CLI Features"]
                FileProcessing["File Processing"]
                BatchOperations["Batch Operations"]
                ConfigManagement["Configuration Management"]
                ColorOutput["Colored Output"]
                ProgressBars["Progress Indicators"]
            end
            
            OriginMarkClass --> CLIFeatures
        end
        
        subgraph SharedCrypto["Shared Cryptographic Operations"]
            Ed25519["Ed25519 Digital Signatures"]
            SHA256["SHA-256 Content Hashing"]
            Base64["Base64 Encoding/Decoding"]
            KeyManagement["Key Pair Management"]
        end
        
        TSCore --> SharedCrypto
        CLICore --> SharedCrypto
        W3Core --> SharedCrypto
        
        subgraph APIIntegration["API Integration"]
            RESTEndpoints["REST API Endpoints"]
            Authentication["Bearer Token Auth"]
            ErrorHandling["Error Handling"]
            RetryLogic["Retry Mechanisms"]
        end
        
        TSSignAPI --> APIIntegration
        TSVerifyAPI --> APIIntegration
        Requests --> APIIntegration
        
        subgraph LocalOperations["Local Operations"]
            OfflineMode["Offline Capability"]
            LocalStorage["Local Key Storage"]
            FileSystemOps["File System Operations"]
            SidecarFiles["Sidecar JSON Files"]
        end
        
        TSSignLocal --> LocalOperations
        TSVerifyLocal --> LocalOperations
        OriginMarkClass --> LocalOperations
    end
    
    style TypeScriptSDK fill:#e8f5e8
    style Web3SDK fill:#e3f2fd
    style PythonCLI fill:#fff3e0
    style SharedCrypto fill:#e3f2fd
    style APIIntegration fill:#fce4ec
    style LocalOperations fill:#f1f8e9
    style TSModern fill:#f3e5f5
    style CLIModern fill:#f3e5f5
```

## Description

This diagram shows the modernized SDK architecture including:

### TypeScript SDK (ts-sdk)
- **ES2022 Target** with NodeNext module resolution
- **libsodium-wrappers** for Ed25519 cryptography
- **Strict TypeScript** configuration
- Support for Node.js 20+ LTS and React 18+

### Web3 SDK (web3-sdk) v3.0
- **ethers.js v6** for blockchain interaction
- **IPFS HTTP Client** for decentralized storage
- **Merkle Tree** support for batch proofs
- On-chain signature registration and verification

### Python CLI (py-cli)
- **pyproject.toml** modern packaging (replaces setup.py)
- **Python 3.10+** type hints (`str | None` syntax)
- **Timezone-aware datetime** (no more `utcnow()`)
- **Ruff** for fast linting, **mypy** for type checking
- **Rich 13.x** for beautiful terminal output