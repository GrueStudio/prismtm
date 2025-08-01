# Prism Task Manager (ptm)

> *Like a prism breaks white light into its component colors, Prism Task Manager breaks complex projects into their constituent tasks, making the invisible work visible and manageable.*

**Hierarchical Task Management for Solo Development**

[![Version](https://img.shields.io/badge/version-0.1.0--dev-orange)](https://github.com/yourusername/prism-task-manager)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-GNU-green.svg)](LICENSE)

## 🎯 What is Prism?

Prism Task Manager bridges the gap between high-level project vision and daily actionable work. It provides a four-tier hierarchical system designed specifically for software development workflows:

- **🎯 Phases** - Strategic milestones (Pre-Alpha, Alpha, Beta, Release)
- **🏁 Milestones** - Major feature collections (0.1.x, 1.0.x, 2.0.x)
- **📦 Blocks** - Version-ready task collections (1.0.0, 1.0.1, 1.0.2)
- **✅ Tasks & Subtasks** - Individual features and granular work items

## ⚡ Quick Start

```bash
# Install (coming soon)
pip install prism-task-manager

# Initialize project
ptm init

# Navigate your project like a filesystem
ptm milestone              # List milestones
ptm block                  # List blocks in current milestone
ptm task                   # List tasks in current block

# Add new work
ptm milestone add "core-features" --version 1.0.x
ptm block add "authentication"
ptm task add "user-login"
ptm subtask add "validate credentials"

# Track time automatically
ptm start                  # Start timer on current subtask
ptm next                   # Move to next item (auto-starts timer)
ptm status                 # See full project overview
```

## 🌟 Key Features

### **Terminal-Centric Navigation**
Navigate your project structure like a filesystem with intuitive commands that feel natural to developers.

### **Automatic Time Tracking**
Built-in timer management with smart auto-start, pause tracking, and detailed analytics to understand where your development time actually goes.

### **Integrated Bug Tracking**
Global bug database with tagging, automatic fix task generation, and cross-project search capabilities.

### **Orphan Task System**
Never lose a good idea - capture tasks and foster them into the right place when you find the perfect home.

### **Version-Aligned Workflow**
Task completion directly correlates with release readiness through the block system.

## 🏗️ Project Status

**Current Phase:** Pre-Alpha (0.x.x)
**Active Milestone:** 0.1.x - Core Foundation
**Next Block:** 0.1.1 - Data Model Design

Prism is currently in early development. We're dogfooding our own methodology to build the tool - check out our [PRISMPLAN.md](PRISMPLAN.md) to see Prism principles in action!

## 📖 Documentation

- **[Getting Started Guide](docs/getting-started.md)** - Your first steps with Prism
- **[Command Reference](docs/commands.md)** - Complete CLI documentation
- **[Workflow Guide](docs/workflow.md)** - Best practices and patterns
- **[Development Plan](PRISMPLAN.md)** - Our own Prism-managed roadmap

## 🤝 Contributing

We welcome contributions! Since we're dogfooding Prism to build itself, contributors will get hands-on experience with the methodology.

1. **Check our [PRISMPLAN.md](PRISMPLAN.md)** to see current priorities
2. **Look for orphan tasks** that need fostering into milestones
3. **Follow our hierarchical approach** when proposing new features

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 🛠️ Development

```bash
# Clone and setup
git clone https://github.com/yourusername/prism-task-manager.git
cd prism-task-manager
pip install -e .

# Run tests
pytest

# Check our own progress
ptm status
```

## 📄 License

GNU General Public License - see [LICENSE](LICENSE) for details.

## 🎨 Philosophy

Traditional task management tools fall short for software development. They're either too simplistic (basic to-do lists) or too rigid (heavyweight project management).

Prism isn't about imposing a new methodology - it's about providing structure around natural development workflows. The system enhances your existing practices by adding hierarchy, progress tracking, time awareness, and clear checkpoints.

The result is a task management system that thinks like a developer, reveals development patterns through time tracking, and scales from small personal projects to complex long-term endeavors.

---

*Built with ❤️ for developers who live in the terminal*
