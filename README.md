# Permía

**The deterministic enforcement infrastructure for regulated industries.**

Permía replaces slow, subjective permit processes with fast, legally-cited outcomes delivered in minutes. It then transforms permits into living assets through continuous verification.

## Tech Stack

- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** Vite + React + TypeScript + Tailwind CSS + shadcn/ui
- **Mobile:** Kotlin Multiplatform Mobile (KMM) + Native UIs (Jetpack Compose + SwiftUI)
- **Database:** PostgreSQL 15+
- **Cloud:** Azure (Blob Storage, Document Intelligence, OpenAI, Computer Vision)

## Repository Structure

```
permia/
├── apps/
│   ├── backend/           # FastAPI - deterministic evaluation engine
│   ├── frontend/          # Web portal (applicant + reviewer)
│   ├── mobile-android/    # Android app (Jetpack Compose)
│   └── mobile-ios/        # iOS app (SwiftUI)
├── packages/
│   ├── mobile-core/       # KMM shared business logic
│   ├── sdk/               # TypeScript SDK (generated from OpenAPI)
│   ├── ui/                # Shared design system
│   ├── rules-validator/   # Rule schema validator
│   ├── eslint-config/     # Shared ESLint config
│   └── tsconfig/          # Shared TypeScript config
├── rules/                 # JSON rule corpus (60 rules)
├── docs/                  # Architecture, API specs, security docs
└── infra/                 # Terraform (Azure infrastructure)
```

## Quick Start

### Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **pnpm** 9.11+
- **Docker** & Docker Compose
- **Android Studio** (for mobile-android)
- **Xcode** 15+ (for mobile-ios, macOS only)

### Setup

```bash
# Clone repository
git clone https://github.com/permia/permia.git
cd permia

# Install dependencies
corepack enable
pnpm install

# Copy environment variables
cp .env.example .env
# Edit .env with your Azure credentials

# Start backend + database
docker-compose up -d

# Generate TypeScript SDK
pnpm sdk:gen

# Run all checks
pnpm typecheck
pnpm lint
pnpm test
pnpm rules:validate
```

### Development

**Backend:**
```bash
cd apps/backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e .
uvicorn src.main:app --reload
```

**Frontend:**
```bash
cd apps/frontend
pnpm dev
```

**Mobile (Android):**
```bash
cd apps/mobile-android
./gradlew installDebug
```

**Mobile (iOS):**
```bash
cd apps/mobile-ios
open Permia.xcworkspace
# Run from Xcode
```

## Testing

```bash
# All tests
pnpm test

# Backend only
cd apps/backend && pytest

# Frontend only
cd apps/frontend && pnpm test

# Rules validation
pnpm rules:validate
```

## Documentation

- [System Architecture](docs/architecture/system-architecture.md)
- [API Documentation](docs/api/README.md)
- [Gate-0 Validation Protocol](docs/gate-0/validation-protocol.md)
- [Developer Setup](docs/onboarding/developer-setup.md)
- [Security](docs/security/SECURITY.md)

## License

Proprietary - Svala Solutions ehf. (kt: 440425-0540)

All rights reserved.
