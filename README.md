# CryptoTronBot Portfolio Tracker

A modern cryptocurrency portfolio tracking application with AI-powered analytics, built with Flask (Python) backend and Sinatra (Ruby) frontend.

## 🚀 Features

- **Portfolio Management**: Track unlimited cryptocurrency holdings
- **Real-time Prices**: Live price updates from CoinGecko API
- **Modern UI/UX**: Beautiful, responsive design with animations
- **AI Analytics**: Premium features with algorithmic insights
- **Security**: JWT authentication and role-based access
- **Containerized**: Docker support for easy deployment
- **Kubernetes Ready**: Production deployment on GKE

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Ruby/Sinatra)│◄──►│   (Flask/Python)│◄──►│   (SQLite)      │
│   Port: 4567    │    │   Port: 5000    │    │   Local File    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

### Required Software
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Ruby 3.2+** - [Download](https://www.ruby-lang.org/en/downloads/)
- **Docker** - [Download](https://docs.docker.com/get-docker/)
- **Git** - [Download](https://git-scm.com/)

### Optional (for production)
- **Google Cloud SDK** - [Install](https://cloud.google.com/sdk/docs/install)
- **kubectl** - [Install](https://kubernetes.io/docs/tasks/tools/)

## 🛠️ Local Development Setup

### Option 1: Traditional Setup (Recommended for Development)

#### 1. Clone the Repository
```bash
git clone https://github.com/iFocus-Innovations-LLC/cryptotronbot-portfolio.git
cd cryptotronbot-portfolio
```

#### 2. Backend Setup (Python/Flask)

```bash
# Navigate to backend directory
cd cryptotronbot_backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Run backend server
python app.py
```

The backend will be available at `http://localhost:5000`

#### 3. Frontend Setup (Ruby/Sinatra)

```bash
# Open new terminal and navigate to frontend directory
cd cryptotronbot_frontend

# Install Ruby dependencies
bundle install

# Run frontend server
ruby app.rb
```

The frontend will be available at `http://localhost:4567`

### Option 2: Docker Setup (Recommended for Testing)

#### Quick Start with Docker
```bash
# Test Docker setup
./test-local.sh

# Run with Docker Compose
docker-compose up
```

This will start:
- Backend on `http://localhost:5000`
- Frontend on `http://localhost:4567`
- Nginx load balancer on `http://localhost:80`

## 🧪 Testing

### Health Checks
```bash
# Backend health
curl http://localhost:5000/api/health

# Frontend health
curl http://localhost:4567/
```

### API Testing
```bash
# Register a new user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'
```

## 📁 Project Structure

```
cryptotronbot-portfolio/
├── cryptotronbot_backend/          # Flask backend
│   ├── app.py                     # Main application
│   ├── models.py                  # Database models
│   ├── requirements.txt           # Python dependencies
│   └── utils/                     # Utility functions
├── cryptotronbot_frontend/        # Sinatra frontend
│   ├── app.rb                    # Main application
│   ├── Gemfile                   # Ruby dependencies
│   ├── views/                    # ERB templates
│   └── public/                   # Static assets
├── k8s/                          # Kubernetes manifests
├── Dockerfile.backend            # Backend container
├── Dockerfile.frontend           # Frontend container
├── docker-compose.yml            # Local development
├── deploy.sh                     # GKE deployment script
└── README.md                     # This file
```

## 🔧 Configuration

### Environment Variables

#### Backend (Flask)
```bash
FLASK_ENV=development
DATABASE_URL=sqlite:///cryptotronbot.db
JWT_SECRET_KEY=your-secret-key
LOG_LEVEL=INFO
```

#### Frontend (Ruby)
```bash
RACK_ENV=development
BACKEND_URL=http://localhost:5000
LOG_LEVEL=INFO
```

## 🚀 Deployment

### Local Docker Testing
```bash
# Test Docker images
./test-local.sh

# Run with Docker Compose
docker-compose up -d
```

### Production Deployment (GKE)
```bash
# Update project ID in deploy.sh
PROJECT_ID="your-gcp-project-id"

# Deploy to Google Kubernetes Engine
./deploy.sh
```

For detailed deployment instructions, see [README-K8S.md](README-K8S.md).

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt password encryption
- **Input Validation**: XSS and injection protection
- **Rate Limiting**: API and login rate limiting
- **HTTPS**: SSL/TLS encryption in production

## 📊 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user profile

### Portfolio
- `GET /api/portfolio` - Get user portfolio
- `POST /api/portfolio/holdings` - Add new holding
- `PUT /api/portfolio/holdings/<id>` - Update holding
- `DELETE /api/portfolio/holdings/<id>` - Delete holding

### Cryptocurrency
- `GET /api/cryptocurrencies` - Get supported cryptocurrencies
- `GET /api/crypto_prices_available` - Get available price data

### Health
- `GET /api/health` - Backend health check

## 🐛 Troubleshooting

### Common Issues

#### Backend Won't Start
```bash
# Check if virtual environment is activated
which python
# Should show: .../venv/bin/python

# Check dependencies
pip list

# Check database
flask db current
```

#### Frontend Won't Start
```bash
# Check Ruby version
ruby --version

# Check dependencies
bundle list

# Check if backend is running
curl http://localhost:5000/api/health
```

#### Docker Issues
```bash
# Check Docker is running
docker info

# Check images
docker images

# Check containers
docker ps -a
```

### Logs
```bash
# Backend logs
tail -f cryptotronbot_backend/app.log

# Frontend logs
tail -f cryptotronbot_frontend/sinatra.log

# Docker logs
docker-compose logs -f
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review the [Kubernetes deployment guide](README-K8S.md)

## 🎯 Roadmap

- [ ] Real-time price updates with WebSockets
- [ ] Advanced portfolio analytics
- [ ] Mobile app development
- [ ] Integration with more exchanges
- [ ] Automated trading features
- [ ] Social features and sharing

---

**Built with ❤️ by the CryptoTronBot Team**


