# Contributing to OPTIC-SHIELD

Thank you for your interest in contributing to OPTIC-SHIELD! This document provides guidelines and information for contributors.

## Table of Contents

- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Contribution Workflow](#contribution-workflow)
- [Testing](#testing)
- [Documentation](#documentation)

## Project Structure

```
OPTIC-SHIELD/
├── device/                          # Raspberry Pi Detection Service
│   ├── config/                      # Configuration files
│   │   ├── config.yaml              # Base configuration
│   │   ├── config.dev.yaml          # Development environment overrides
│   │   ├── config.prod.yaml         # Production environment overrides
│   │   └── .env.example             # Environment variables template
│   │
│   ├── src/                         # Source code
│   │   ├── core/                    # Core detection components
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Configuration management system
│   │   │   ├── detector.py          # YOLO11n + NCNN wildlife detector
│   │   │   └── camera.py            # Camera management (Pi Camera + USB)
│   │   │
│   │   ├── storage/                 # Data persistence
│   │   │   ├── __init__.py
│   │   │   ├── database.py          # SQLite database for detections
│   │   │   └── image_store.py       # Image storage and compression
│   │   │
│   │   ├── services/                # Background services
│   │   │   ├── __init__.py
│   │   │   ├── detection_service.py # Main detection orchestration
│   │   │   └── alert_service.py     # Alert handling (local + remote)
│   │   │
│   │   ├── api/                     # External communication
│   │   │   ├── __init__.py
│   │   │   └── dashboard_client.py  # Dashboard API client
│   │   │
│   │   └── utils/                   # Utilities
│   │       ├── __init__.py
│   │       ├── logging_setup.py     # Logging configuration
│   │       └── system_monitor.py    # Resource monitoring
│   │
│   ├── scripts/                     # Deployment and utility scripts
│   │   ├── export_model.py          # YOLO to NCNN export script
│   │   ├── setup_rpi.sh             # Raspberry Pi setup automation
│   │   ├── install_service.sh       # Systemd service installer
│   │   └── optic-shield.service     # Systemd service definition
│   │
│   ├── models/                      # YOLO model files (gitignored)
│   ├── data/                        # Runtime data (gitignored)
│   ├── logs/                        # Log files (gitignored)
│   ├── main.py                      # Application entry point
│   └── requirements.txt             # Python dependencies
│
├── dashboard/                       # Vercel Web Dashboard (Next.js)
│   ├── src/
│   │   ├── app/                     # Next.js App Router
│   │   │   ├── page.tsx             # Main dashboard page
│   │   │   ├── layout.tsx           # Root layout
│   │   │   ├── globals.css          # Global styles
│   │   │   └── api/                 # API routes
│   │   │       ├── devices/
│   │   │       │   ├── route.ts     # Device registration
│   │   │       │   ├── heartbeat/
│   │   │       │   │   └── route.ts # Device heartbeat endpoint
│   │   │       │   └── detections/
│   │   │       │       ├── route.ts # Single detection submission
│   │   │       │       └── batch/
│   │   │       │           └── route.ts # Batch detection submission
│   │   │       ├── detections/
│   │   │       │   └── route.ts     # Get detections
│   │   │       └── stats/
│   │   │           └── route.ts     # Dashboard statistics
│   │   │
│   │   ├── components/              # React components
│   │   │   ├── DeviceCard.tsx       # Device status card
│   │   │   ├── DetectionList.tsx    # Detection list view
│   │   │   └── StatsOverview.tsx    # Statistics overview
│   │   │
│   │   ├── lib/                     # Utilities and helpers
│   │   │   └── auth.ts              # Authentication and data stores
│   │   │
│   │   └── types/                   # TypeScript type definitions
│   │       └── index.ts             # Shared types
│   │
│   ├── public/                      # Static assets
│   ├── package.json                 # Node.js dependencies
│   ├── tsconfig.json                # TypeScript configuration
│   ├── next.config.js               # Next.js configuration
│   ├── tailwind.config.js           # Tailwind CSS configuration
│   ├── postcss.config.js            # PostCSS configuration
│   ├── vercel.json                  # Vercel deployment config
│   ├── .env.example                 # Environment variables template
│   └── README.md                    # Dashboard documentation
│
├── docs/                            # Documentation
│   ├── setup-rpi.md                 # Raspberry Pi setup guide
│   └── setup-dashboard.md           # Dashboard deployment guide
│
├── README.md                        # Main project documentation
├── CONTRIBUTING.md                  # This file
├── LICENSE                          # Project license
└── .gitignore                       # Git ignore rules
```

## Development Setup

### Prerequisites

- **For Device Service**:
  - Python 3.9-3.12
  - Raspberry Pi 5 (for testing) or Linux system
  - Camera (Pi Camera Module 3 or USB camera)

- **For Dashboard**:
  - Node.js 18+
  - npm or yarn

### Device Service Setup

```bash
# Clone repository
git clone https://github.com/yourusername/OPTIC-SHIELD.git
cd OPTIC-SHIELD/device

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp config/.env.example config/.env

# Run in development mode
OPTIC_ENV=development python main.py
```

### Dashboard Setup

```bash
cd OPTIC-SHIELD/dashboard

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Run development server
npm run dev
```

## Code Standards

### Python (Device Service)

- **Style**: Follow PEP 8
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings
- **Line Length**: Maximum 100 characters
- **Imports**: Group imports (standard library, third-party, local)

Example:
```python
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


def process_detection(
    image: np.ndarray,
    confidence_threshold: float = 0.5
) -> List[Detection]:
    """
    Process an image for wildlife detection.
    
    Args:
        image: RGB image as numpy array
        confidence_threshold: Minimum confidence for detections
        
    Returns:
        List of Detection objects
    """
    pass
```

### TypeScript/React (Dashboard)

- **Style**: Use Prettier for formatting
- **Components**: Use functional components with hooks
- **Types**: Define explicit types, avoid `any`
- **Naming**: 
  - Components: PascalCase
  - Functions: camelCase
  - Constants: UPPER_SNAKE_CASE

Example:
```typescript
interface DetectionProps {
  detection: Detection
  onSelect?: (id: number) => void
}

export default function DetectionCard({ detection, onSelect }: DetectionProps) {
  // Component implementation
}
```

## Contribution Workflow

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/OPTIC-SHIELD.git
cd OPTIC-SHIELD
```

### 2. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 3. Make Changes

- Write clean, documented code
- Follow the code standards above
- Add tests for new features
- Update documentation as needed

### 4. Test Your Changes

**Device Service:**
```bash
cd device
source venv/bin/activate
python -m pytest  # If tests exist
python main.py    # Manual testing
```

**Dashboard:**
```bash
cd dashboard
npm run lint
npm run build
npm run dev  # Manual testing
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add wildlife species classification"

# Use conventional commits:
# feat: New feature
# fix: Bug fix
# docs: Documentation changes
# style: Code style changes
# refactor: Code refactoring
# test: Test additions/changes
# chore: Build/tooling changes
```

### 6. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# Provide clear description of changes
```

## Testing

### Device Service Testing

Create tests in `device/tests/`:

```python
# tests/test_detector.py
import pytest
from src.core.detector import WildlifeDetector

def test_detector_initialization():
    detector = WildlifeDetector(
        model_path="models/test_model",
        confidence_threshold=0.5
    )
    assert detector.confidence_threshold == 0.5
```

Run tests:
```bash
pytest -v
```

### Dashboard Testing

Add tests for components and API routes:

```typescript
// __tests__/components/DeviceCard.test.tsx
import { render, screen } from '@testing-library/react'
import DeviceCard from '@/components/DeviceCard'

test('renders device name', () => {
  const device = { id: '1', name: 'Test Device', ... }
  render(<DeviceCard device={device} />)
  expect(screen.getByText('Test Device')).toBeInTheDocument()
})
```

## Documentation

### Code Documentation

- Add docstrings to all public functions/classes
- Include type hints
- Document complex algorithms
- Add inline comments for non-obvious code

### README Updates

When adding features:
- Update main README.md
- Update relevant docs in `docs/`
- Add examples if applicable

### API Documentation

When modifying API endpoints:
- Update `docs/setup-dashboard.md`
- Document request/response formats
- Include example curl commands

## Areas for Contribution

### High Priority

- [ ] Add unit tests for core modules
- [ ] Implement database persistence for dashboard
- [ ] Add support for custom YOLO models
- [ ] Improve error handling and logging
- [ ] Add WebSocket support for real-time updates

### Features

- [ ] Multi-camera support per device
- [ ] Video recording on detection
- [ ] Email/SMS alert integration
- [ ] Mobile app for dashboard
- [ ] Detection confidence tuning UI
- [ ] Export detection data (CSV, JSON)

### Documentation

- [ ] API reference documentation
- [ ] Deployment best practices
- [ ] Performance tuning guide
- [ ] Troubleshooting guide
- [ ] Video tutorials

### Infrastructure

- [ ] Docker support
- [ ] CI/CD pipeline
- [ ] Automated testing
- [ ] Performance benchmarks

## Questions or Issues?

- **Bug Reports**: Open an issue with detailed description
- **Feature Requests**: Open an issue with use case explanation
- **Questions**: Use GitHub Discussions
- **Security Issues**: Email directly (do not open public issue)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other contributors

Thank you for contributing to OPTIC-SHIELD! 🦁🛡️
