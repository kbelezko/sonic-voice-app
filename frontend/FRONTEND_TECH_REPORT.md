# Frontend Technology Stack Report

## Project Overview
**Project Name:** book-hotel-kiro (Frontend)  
**Version:** 0.1.0  
**Location:** `/Users/kbelz/Desktop/Dev/book-hotel-kiro/frontend`

---

## Core Framework

### Next.js 16.4.0
- **Type:** React Meta-Framework
- **Purpose:** Full-stack React framework with server-side rendering
- **Key Features:**
  - App Router architecture
  - Server Components
  - Built-in routing
  - API routes support
  - Automatic code splitting
  - Hot module replacement

---

## UI Library

### React 19.3.0
- **Type:** UI Library
- **Purpose:** Component-based UI development
- **Companion:** react-dom@19.3.0 for DOM rendering
- **Key Features:**
  - Latest React 19 features
  - Concurrent rendering
  - Automatic batching
  - Enhanced hooks

---

## Styling

### Tailwind CSS 4.3.3
- **Type:** Utility-first CSS Framework
- **Purpose:** Rapid UI development with utility classes
- **Integration:** @tailwindcss/turbopack@4.3.3 for Next.js integration
- **Key Features:**
  - Utility-first workflow
  - JIT (Just-In-Time) compilation
  - Dark mode support
  - Responsive design utilities
  - Custom design system

---

## Icon Library

### Lucide React 1.52.0
- **Type:** Icon Library
- **Purpose:** Beautiful, consistent SVG icons
- **Key Features:**
  - 1000+ icons
  - Tree-shakeable
  - Customizable size and color
  - TypeScript support

---

## Development Tools

### TypeScript 5.9.3
- **Type:** Programming Language
- **Purpose:** Type-safe JavaScript development
- **Key Features:**
  - Static type checking
  - Enhanced IDE support
  - Better code documentation
  - Improved refactoring

### ESLint 9.39.5
- **Type:** Linting Tool
- **Purpose:** Code quality and consistency
- **Configuration:** eslint-config-next@16.4.0 (Next.js optimized rules)
- **Key Features:**
  - Code quality enforcement
  - Best practices validation
  - Automated code review

---

## Type Definitions

- **@types/node@20.19.43** - Node.js type definitions
- **@types/react@19.3.0** - React type definitions
- **@types/react-dom@19.3.0** - React DOM type definitions
- **@types/ws@8.18.2** - WebSocket type definitions

---

## Communication Protocol

### Native WebSocket API
- **Type:** Browser API
- **Purpose:** Real-time bidirectional communication
- **Use Case:** Voice chat with backend (FastAPI)
- **Data Format:** JSON messages with base64-encoded PCM audio

---

## Build System

### Turbopack (via Next.js 16)
- **Type:** Bundler
- **Purpose:** Fast incremental builds
- **Integration:** Built into Next.js 16
- **Key Features:**
  - Rust-based for speed
  - Incremental compilation
  - HMR (Hot Module Replacement)
  - Optimized for development

---

## Project Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── page.tsx           # Main conversation page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ConversationWindow.tsx
│   ├── MessageBubble.tsx
│   ├── VoiceButton.tsx
│   └── ErrorBoundary.tsx
├── lib/                   # Utilities
│   └── useVoiceChat.ts   # WebSocket hook
├── package.json           # Dependencies
└── next.config.ts         # Next.js config
```

---

## Key Dependencies Summary

| Package | Version | Category | Purpose |
|---------|---------|----------|---------|
| next | 16.4.0 | Framework | React meta-framework |
| react | 19.3.0 | Library | UI library |
| react-dom | 19.3.0 | Library | React DOM rendering |
| tailwindcss | 4.3.3 | Styling | Utility-first CSS |
| lucide-react | 1.52.0 | Icons | SVG icon library |
| typescript | 5.9.3 | Language | Type-safe JavaScript |
| eslint | 9.39.5 | Tooling | Code linting |

---

## Development Commands

```bash
npm install          # Install dependencies
npm run dev         # Start dev server (http://localhost:3000)
npm run build       # Production build
npm run start       # Start production server
npm run lint        # Run ESLint
```

---

## Browser Requirements

- Modern browsers with WebSocket support
- Web Audio API support (for audio processing)
- MediaRecorder API support (for audio capture)
- ES6+ JavaScript support

---

## Notable Features

1. **Voice-First UI**: Microphone-based conversation interface
2. **Real-time Audio**: PCM audio streaming at 16kHz
3. **TypeScript**: Fully typed codebase
4. **Responsive Design**: Mobile and desktop support via Tailwind
5. **Error Boundaries**: Graceful error handling
6. **WebSocket**: Persistent connection for low-latency communication

---

## npm Commands for Package Information

```bash
# View all dependencies with versions
npm list --depth=0

# View dependency tree
npm list

# View outdated packages
npm outdated

# View package details
npm view <package-name>

# View package info for specific dependency
npm info next
npm info react
npm info tailwindcss
```

---

*Report generated for book-hotel-kiro frontend*
