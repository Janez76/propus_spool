# Contributing to Propus Spool

Thank you for your interest in contributing to Propus Spool! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/propus_spool.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit and push
7. Create a Pull Request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Janez76/propus_spool.git
cd propus_spool

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Use type hints where appropriate

Example:
```python
def process_reading(db: Session, reading: WeightReadingCreate) -> dict:
    """
    Process a weight reading from a scale device
    
    Args:
        db: Database session
        reading: Weight reading data
        
    Returns:
        dict with processing results
    """
    # Implementation
```

## Project Structure

```
app/
├── models/         # Database models (SQLAlchemy)
├── schemas/        # Pydantic schemas for validation
├── routers/        # API route handlers
├── services/       # Business logic
├── clients/        # External API clients
└── workers/        # Background tasks
```

## Making Changes

### Adding a New Endpoint

1. Create or update a router in `app/routers/`
2. Create schemas in `app/schemas/`
3. Implement business logic in `app/services/`
4. Update documentation

### Adding a Database Model

1. Add model to `app/models/__init__.py`
2. Create migration (if using Alembic)
3. Update related schemas
4. Update services using the model

### Adding an External Integration

1. Create client in `app/clients/`
2. Implement service methods in `app/services/`
3. Add configuration options to `app/config.py`
4. Update `.env.example`

## Testing

Before submitting a PR:

1. Test manually:
```bash
# Start the server
uvicorn app.main:app --reload

# Test endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/readings \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "uid": "123", "gross_weight_g": 100}'
```

2. Test Docker build:
```bash
docker build -t propus_spool:test .
```

3. Test Docker Compose:
```bash
docker compose up -d
docker compose ps
docker compose logs app
docker compose down
```

## Commit Messages

Use clear, descriptive commit messages:

```
Add endpoint for batch weight readings

- Add POST /api/v1/readings/batch endpoint
- Update schemas for batch operations
- Add service method for batch processing
- Update API documentation
```

Format:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description (if needed)
- List changes with bullet points

## Pull Request Process

1. **Update documentation** if you add/change features
2. **Test your changes** thoroughly
3. **Update CHANGELOG** (if exists) with your changes
4. **Describe your PR** clearly:
   - What does it do?
   - Why is it needed?
   - How was it tested?

## Feature Requests

Open an issue with:
- Clear description of the feature
- Use case / problem it solves
- Proposed implementation (if any)

## Bug Reports

Open an issue with:
- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Docker version, etc.)
- Logs (if applicable)

## Code Review

All PRs require review before merging. Reviewers will check:
- Code quality and style
- Documentation
- Testing
- Breaking changes
- Security implications

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open an issue for questions
- Check existing issues and PRs
- Read the documentation

## Areas for Contribution

We welcome contributions in these areas:

### High Priority
- [ ] Unit tests and test coverage
- [ ] Integration tests
- [ ] CI/CD pipeline
- [ ] Performance optimization
- [ ] Database migration system

### Features
- [ ] Web UI dashboard
- [ ] Klipper/Moonraker integration
- [ ] Bambu Lab printer integration
- [ ] Mobile app
- [ ] Advanced analytics
- [ ] Multi-user support with authentication
- [ ] Prometheus metrics
- [ ] Grafana dashboards

### Documentation
- [ ] Video tutorials
- [ ] More deployment examples
- [ ] API client libraries (Python, JavaScript)
- [ ] ESP32 example code
- [ ] Home Assistant integration guide

### Infrastructure
- [ ] Multi-arch Docker images (ARM64, AMD64)
- [ ] Kubernetes deployment files
- [ ] Helm chart
- [ ] Automated releases

## Getting Help

- Read the [README.md](README.md)
- Check [QUICKSTART.md](QUICKSTART.md)
- Review [API_EXAMPLES.md](API_EXAMPLES.md)
- See [DEPLOYMENT.md](DEPLOYMENT.md)
- Open an issue

Thank you for contributing! 🎉
