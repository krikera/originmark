# OriginMark Flow Diagrams

This folder contains comprehensive Mermaid diagrams showing how each component of the OriginMark system works.

##  Available Diagrams

1. **[API Architecture](01-api-architecture.md)** - Complete FastAPI backend architecture
2. **[Browser Extension Flow](02-browser-extension.md)** - Chrome extension (Manifest V3)
3. **[GitHub Integration Scripts](03-github-integration.md)** - CI/CD and local Git workflows
4. **[SDK Architecture](04-sdk-architecture.md)** - TypeScript, Web3, and Python SDK components
5. **[Web Dashboard Flow](05-web-dashboard.md)** - Next.js 15 web application flow
6. **[System Overview](06-system-overview.md)** - High-level system architecture

## 🛠 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Web Dashboard | Next.js + Turbopack | 15.x |
| UI Framework | React | 18.x |
| Animations | Framer Motion | 11.x |
| Styling | TailwindCSS | 3.4.x |
| TypeScript SDK | TypeScript + ES2022 | 5.x |
| Web3 SDK | ethers.js | 6.x |
| Python CLI | Python + Rich | 3.10+ |
| Browser Extension | Chrome MV3 | 1.0.0 |
| API | FastAPI + SQLAlchemy | - |

##  How to Use These Diagrams

### Option 1: Online Viewers
Copy the Mermaid code from any `.md` file and paste it into:
- [Mermaid Live Editor](https://mermaid.live/) - Interactive online editor
- [GitHub](https://github.com) - GitHub automatically renders Mermaid diagrams
- [GitLab](https://gitlab.com) - GitLab also supports Mermaid rendering

### Option 2: Export as Images
Using the Mermaid CLI to convert to images:

```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Convert to PNG
mmdc -i 01-api-architecture.md -o 01-api-architecture.png

# Convert to SVG
mmdc -i 01-api-architecture.md -o 01-api-architecture.svg

# Convert all diagrams
for file in *.md; do
  mmdc -i "$file" -o "${file%.md}.png"
done
```

### Option 3: VS Code Extension
Install the "Mermaid Markdown Syntax Highlighting" extension to view diagrams directly in VS Code.

##  Diagram Details

### 01-api-architecture.md
- Authentication flow with API keys
- Core endpoints for signing and verification
- Database schema and relationships
- Webhook system for notifications

### 02-browser-extension.md
- **Manifest V3** architecture with Service Worker
- **ES2022+** modern JavaScript patterns
- Auto-detection and inline badges
- XSS protection and CSP

### 03-github-integration.md
- GitHub Actions for automated signing
- Pre-commit hooks
- File detection and filtering

### 04-sdk-architecture.md
- **TypeScript SDK** (ES2022, NodeNext modules)
- **Web3 SDK** (ethers.js v6, IPFS, Merkle trees)
- **Python CLI** (pyproject.toml, Python 3.10+)

### 05-web-dashboard.md
- **Next.js 15** with Turbopack
- **Framer Motion** animations
- **Sonner** toast notifications
- **Lucide React** icons
- Glassmorphism design

### 06-system-overview.md
- Complete system architecture
- Modern technology stack
- Blockchain integration layer
- Security boundaries

##  Use Cases

These diagrams are perfect for:
- **Documentation** - Technical documentation and user guides
- **Presentations** - System architecture presentations
- **Onboarding** - New developer orientation
- **Planning** - System design and improvement planning

##  Contributing

1. Edit the Mermaid code in the respective `.md` file
2. Test the diagram in [Mermaid Live Editor](https://mermaid.live/)
3. Update the description section
4. Submit a pull request

For more information about Mermaid syntax, visit the [Mermaid Documentation](https://mermaid-js.github.io/mermaid/).