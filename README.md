# Vendor Security Analyzer Web Application

AI-powered compliance analysis for vendor security assessments. This web application provides a modern interface for analyzing vendor documents against security compliance frameworks.

## Features

- **Document Upload**: Drag & drop support for PDF, DOCX, XLSX, XLS, CSV, TXT, MD files
- **Framework Selection**: Analyze against SOC 2, ISO 27001, NIST CSF, HIPAA, GDPR, PCI DSS
- **Real-time Progress**: WebSocket-based streaming of analysis progress
- **AI Chat**: Interactive chat with Claude to ask questions about your compliance analysis
- **Results Dashboard**: Visualizations of compliance scores, findings, and risk assessment
- **Export Options**: Download results as JSON or PDF reports
- **Dark/Light Mode**: Full theme support

## Architecture

- **Frontend**: Next.js 14 + React 18 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python)
- **AI**: AWS Bedrock with Claude
- **Real-time**: WebSockets for progress streaming and chat

## Prerequisites

- Node.js 18+
- Python 3.11+
- AWS Bedrock API Key (recommended) or IAM credentials with Bedrock access
- libmagic (for file type detection)

### Creating a Bedrock API Key

1. Go to the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/home#/api-keys)
2. Click "Create API key"
3. Copy the generated key and save it securely

### Installing libmagic

**macOS:**
```bash
brew install libmagic
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libmagic1
```

## Quick Start

### 1. Clone and Setup

```bash
cd ~/Programming/vendor-security-analyzer-web
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your AWS configuration

# Start the backend
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 4. Access the Application

Open http://localhost:3001 in your browser.

## Docker Deployment

The easiest way to run the application is using Docker.

### Prerequisites

- Docker and Docker Compose installed
- AWS credentials with Bedrock access

### Quick Start with Docker

1. **Clone the repository:**
   ```bash
   git clone https://github.com/alex-colclough/vendor-risk-analyer-web.git
   cd vendor-risk-analyer-web
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your Bedrock API key (recommended):
   ```env
   AWS_BEARER_TOKEN_BEDROCK=your_bedrock_api_key_here
   AWS_REGION=us-east-1
   BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
   ```

   > **Note**: API keys require using an inference profile ID with a geographic prefix (`us.`, `eu.`, `apac.`)

   Or use IAM credentials (alternative):
   ```env
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_REGION=us-east-1
   ```

3. **Build and start the containers:**
   ```bash
   docker compose up --build
   ```

   Or run in detached mode:
   ```bash
   docker compose up --build -d
   ```

4. **Access the application:**
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:8000
   - API Health Check: http://localhost:8000/health

### Docker Commands

| Command | Description |
|---------|-------------|
| `docker compose up --build` | Build and start all services |
| `docker compose up -d` | Start services in background |
| `docker compose down` | Stop all services |
| `docker compose logs -f` | View logs (follow mode) |
| `docker compose logs backend` | View backend logs only |
| `docker compose logs frontend` | View frontend logs only |
| `docker compose ps` | Check container status |
| `docker compose restart` | Restart all services |

### Container Details

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 8000 | FastAPI server with WebSocket support |
| `frontend` | 3001 | Next.js production server |

### Volumes

- `upload_data`: Persists uploaded files between container restarts

### Rebuilding After Changes

If you make changes to the code:
```bash
docker compose down
docker compose up --build
```

To rebuild a specific service:
```bash
docker compose build backend
docker compose up -d
```

## Configuration

### Backend Environment Variables

#### AWS Authentication (choose one)

| Variable | Description |
|----------|-------------|
| `AWS_BEARER_TOKEN_BEDROCK` | **Recommended**: Bedrock API key for simple authentication |
| `AWS_ACCESS_KEY_ID` | Alternative: IAM access key ID |
| `AWS_SECRET_ACCESS_KEY` | Alternative: IAM secret access key |
| `AWS_ROLE_ARN` | Optional: IAM role ARN for role assumption |

#### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `BEDROCK_MODEL_ID` | Claude inference profile ID | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `BEDROCK_MAX_TOKENS` | Max response tokens | `4096` |
| `BEDROCK_TEMPERATURE` | Model temperature | `0.3` |
| `MAX_FILE_SIZE_MB` | Max upload file size | `100` |
| `MAX_TOTAL_SIZE_MB` | Max total session size | `500` |
| `DEBUG` | Enable debug mode | `false` |

### Frontend Environment Variables

Create `.env.local` in the frontend directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/upload` | POST | Upload documents |
| `/api/v1/upload/{session_id}` | GET | List uploaded files |
| `/api/v1/upload/{session_id}/{file_id}` | DELETE | Remove file |
| `/api/v1/analysis/start` | POST | Start analysis |
| `/api/v1/analysis/{id}/status` | GET | Get status |
| `/api/v1/analysis/{id}/results` | GET | Get results |
| `/api/v1/connection/test` | POST | Test AWS Bedrock |
| `/api/v1/export/json/{id}` | GET | Download JSON |
| `/api/v1/export/pdf/{id}` | GET | Download PDF |
| `/ws/analysis/{session_id}` | WS | Progress stream |
| `/ws/chat/{session_id}` | WS | Chat stream |

## Security Features

- File validation with magic number checks
- Path traversal prevention
- Input sanitization with Pydantic
- Rate limiting
- CORS configuration
- Security headers (X-Frame-Options, CSP, etc.)
- Session-based file isolation
- No credentials in logs

## Project Structure

```
vendor-security-analyzer-web/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration
│   │   ├── api/
│   │   │   ├── routes/          # API endpoints
│   │   │   └── websocket/       # WebSocket handlers
│   │   ├── services/            # Business logic
│   │   └── models/              # Pydantic models
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom hooks
│   │   ├── lib/                 # Utilities
│   │   ├── store/               # Zustand store
│   │   └── types/               # TypeScript types
│   └── package.json
│
└── README.md
```

## Development

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Building for Production

```bash
# Backend
cd backend
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
cd frontend
npm run build
npm start
```

## License

MIT
