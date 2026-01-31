# GitHub Integration Scripts

```mermaid
graph TB
    subgraph "GitHub Integration Architecture"
        
        subgraph GitHubActions["GitHub Actions Workflow"]
            PushTrigger[Push to main/develop] --> ActionStart[Workflow Start]
            PRTrigger[Pull Request] --> ActionStart
            ReleaseTrigger[Release Published] --> ActionStart
            
            ActionStart --> Setup[Setup Environment<br/>Python + Node.js + OriginMark CLI]
            Setup --> DetectFiles[Detect Files to Sign<br/>*.py, *.ts, *.js, *.md]
            
            DetectFiles --> SignFiles[Sign Files in Parallel]
            
            subgraph SignFiles["File Signing Process"]
                PythonFiles[Sign Python Files]
                JSFiles[Sign TypeScript/JS Files]
                DocsFiles[Sign Documentation]
            end
            
            SignFiles --> VerifyStep[Verify All Signatures]
            VerifyStep --> CreateManifest[Create Signature Manifest]
            
            CreateManifest --> Conditional{Event Type?}
            Conditional -->|Push to main| CommitSigs[Commit Signature Files]
            Conditional -->|Pull Request| PRComment[Add PR Comment]
            Conditional -->|Release| UploadArtifacts[Upload Release Artifacts]
            
            CommitSigs --> GitPush[Push Signatures to Repo]
            PRComment --> SignatureReport[Generate Signature Report]
            UploadArtifacts --> ReleaseAssets[Attach to Release]
        end
        
        subgraph LocalScript["Local GitHub Integration Script"]
            DevWorkflow[Developer Workflow] --> LocalScript_Start[Run github-integration.py]
            
            LocalScript_Start --> GitInfo[Extract Git Information<br/>• Commit hash<br/>• Branch<br/>• Author<br/>• Remote URL]
            
            GitInfo --> CommandSelect{Command Selection}
            
            CommandSelect -->|sign| SignCommand[Sign Files Command]
            CommandSelect -->|verify| VerifyCommand[Verify Repository]
            CommandSelect -->|manifest| ManifestCommand[Create Manifest]
            CommandSelect -->|pre-commit| PreCommitHook[Pre-commit Hook]
            
            subgraph SignCommand["Sign Command Flow"]
                FileDetection[File Detection Logic<br/>• Changed files<br/>• All files<br/>• Specific files]
                FilterFiles[Filter Signable Files<br/>Skip .git, node_modules]
                LocalSign[Local CLI Signing]
                APISign[API-based Signing]
            end
            
            subgraph VerifyCommand["Verify Command Flow"]
                FindSigFiles[Find .originmark.json Files]
                VerifyEach[Verify Each Signature]
                ReportResults[Generate Verification Report]
            end
            
            subgraph PreCommitHook["Pre-commit Hook Flow"]
                StagedFiles[Get Staged Files]
                SignStaged[Sign Staged Files]
                AddSigFiles[Stage Signature Files]
            end
            
            SignCommand --> SignResult[Signing Statistics]
            VerifyCommand --> VerifyResult[Verification Results]
            ManifestCommand --> ManifestFile[originmark-manifest.json]
            PreCommitHook --> HookComplete[Pre-commit Complete]
        end
        
        subgraph Integration["Integration Points"]
            CICD[CI/CD Pipeline Integration]
            DevTools[Developer Tools Integration]
            RepoSecurity[Repository Security]
        end
        
        GitHubActions --> CICD
        LocalScript_Start --> DevTools
        Both --> RepoSecurity
        
        subgraph Security["Security Features"]
            CodeIntegrity[Code Integrity Verification]
            AuthorAttribution[Author Attribution]
            TamperDetection[Tamper Detection]
            AuditTrail[Audit Trail]
        end
        
        Integration --> Security
    end
    
    style GitHubActions fill:#f0f7ff
    style LocalScript fill:#f7fff0
    style Integration fill:#fff7f0
    style Security fill:#fff0f7
```

## Description
This diagram details both automated GitHub Actions workflows and local Git integration scripts, showing how OriginMark integrates with developer workflows for automatic code signing and verification.