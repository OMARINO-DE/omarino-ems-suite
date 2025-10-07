# OMARINO EMS Web Application

Modern web interface for the OMARINO Energy Management System, built with Next.js 14, TypeScript, and React 18.

## 🚀 Features

- **Dashboard**: Real-time monitoring and system overview
- **Time Series**: Historical energy data visualization
- **Forecasts**: Energy demand predictions with multiple models
- **Optimization**: Battery dispatch and asset optimization
- **Scheduler**: Workflow automation and scheduling
- **Authentication**: Secure access with JWT tokens
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Data Visualization**: Interactive charts with Recharts
- **Real-time Updates**: SWR for efficient data fetching

## 📋 Prerequisites

- Node.js 18+ and npm/yarn
- Running OMARINO EMS backend services (API Gateway on port 8080)

## 🛠️ Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Edit .env.local with your configuration
# Set NEXT_PUBLIC_API_URL to your API Gateway URL
```

## 🔧 Configuration

Edit `.env.local`:

```env
# API Gateway URL
NEXT_PUBLIC_API_URL=http://localhost:8080

# NextAuth.js Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-change-in-production
```

## 🏃 Running the Application

### Development Mode

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Production Build

```bash
# Build the application
npm run build

# Start production server
npm start
```

### Type Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

## 🐳 Docker Deployment

### Build Docker Image

```bash
docker build -t omarino-ems-webapp:latest .
```

### Run with Docker

```bash
docker run -d \
  --name omarino-webapp \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://api-gateway:8080 \
  omarino-ems-webapp:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  webapp:
    build: ./webapp
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api-gateway:8080
      - NEXTAUTH_URL=http://localhost:3000
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
    depends_on:
      - api-gateway
    networks:
      - omarino-network

networks:
  omarino-network:
    driver: bridge
```

## 📁 Project Structure

```
webapp/
├── src/
│   ├── app/                    # Next.js 14 App Router
│   │   ├── layout.tsx          # Root layout with providers
│   │   ├── page.tsx            # Home page
│   │   ├── dashboard/          # Dashboard page
│   │   ├── timeseries/         # Time series page
│   │   ├── forecasts/          # Forecasts page
│   │   ├── optimization/       # Optimization page
│   │   ├── scheduler/          # Scheduler page
│   │   └── globals.css         # Global styles
│   ├── components/             # React components
│   │   ├── Navigation.tsx      # Main navigation
│   │   └── Providers.tsx       # Context providers
│   └── lib/                    # Utilities and API client
│       └── api.ts              # API client with typed endpoints
├── public/                     # Static assets
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript configuration
├── next.config.js              # Next.js configuration
├── tailwind.config.js          # Tailwind CSS configuration
├── Dockerfile                  # Docker configuration
└── README.md                   # This file
```

## 🎨 Technology Stack

### Core
- **Next.js 14**: React framework with App Router
- **React 18**: UI library
- **TypeScript**: Type safety

### UI & Styling
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Icon library
- **Recharts**: Data visualization charts

### Data Fetching & State
- **SWR**: React Hooks for data fetching
- **Axios**: HTTP client
- **Zustand**: State management

### Forms & Validation
- **React Hook Form**: Form management
- **Zod**: Schema validation

### Authentication
- **NextAuth.js**: Authentication for Next.js

## 🌐 Pages

### Home (`/`)
- Welcome page with quick links
- System overview cards
- Quick actions

### Dashboard (`/dashboard`)
- Real-time system metrics
- Service health status
- Energy consumption charts
- Battery dispatch visualization
- Recent activity feed

### Time Series (`/timeseries`)
- List of all meters
- Meter details and metadata
- Data import functionality

### Forecasts (`/forecasts`)
- Available forecast models
- Recent forecast runs
- Model comparison
- Create new forecast

### Optimization (`/optimization`)
- Optimization types (battery, demand, cost)
- Recent optimization runs
- Results visualization
- Create new optimization

### Scheduler (`/scheduler`)
- Active workflows
- Recent executions
- Workflow creation and management
- Execution monitoring

## 🔌 API Integration

The application communicates with the OMARINO EMS backend services through the API Gateway. The API client (`src/lib/api.ts`) provides typed methods for all endpoints:

```typescript
import { api } from '@/lib/api'

// Authentication
const { token } = await api.auth.login({ username, password })

// Time Series
const meters = await api.timeseries.getMeters()
const data = await api.timeseries.getSeriesData(seriesId, { start, end })

// Forecasts
const models = await api.forecasts.listModels()
const forecast = await api.forecasts.runForecast('arima', params)

// Optimization
const types = await api.optimization.listTypes()
const optimization = await api.optimization.createOptimization(params)

// Scheduler
const workflows = await api.scheduler.getWorkflows()
const execution = await api.scheduler.triggerWorkflow(workflowId)
```

## 🎯 Data Fetching with SWR

The application uses SWR for efficient data fetching with automatic caching and revalidation:

```typescript
import useSWR from 'swr'
import { api } from '@/lib/api'

function MyComponent() {
  const { data, error, isLoading } = useSWR(
    '/api/timeseries/meters',
    () => api.timeseries.getMeters()
  )

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>

  return <div>{/* Render data */}</div>
}
```

## 🔐 Authentication

The application supports JWT-based authentication through the API Gateway:

1. User logs in with credentials
2. API Gateway returns JWT token
3. Token is stored in localStorage
4. Token is automatically included in all API requests
5. On 401 response, user is redirected to login

## 📊 Charts and Visualization

The application uses Recharts for data visualization:

```typescript
import { LineChart, Line, XAxis, YAxis } from 'recharts'

<LineChart data={data}>
  <XAxis dataKey="timestamp" />
  <YAxis />
  <Line type="monotone" dataKey="value" stroke="#0ea5e9" />
</LineChart>
```

## 🚨 Error Handling

The API client includes automatic error handling:

- Network errors are caught and displayed
- 401 errors trigger logout and redirect to login
- Error messages are user-friendly
- Loading states are managed automatically with SWR

## 🧪 Development Tips

### Hot Reload
Next.js automatically reloads when you save files during development.

### Type Checking
Run `npm run type-check` to check for TypeScript errors without building.

### API Mocking
For development without backend, you can mock API responses in `src/lib/api.ts`.

### Environment Variables
- Variables starting with `NEXT_PUBLIC_` are exposed to the browser
- Other variables are only available server-side
- Restart dev server after changing `.env.local`

## 🐛 Troubleshooting

### "Cannot connect to API Gateway"
- Verify API Gateway is running on the configured URL
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify CORS settings on API Gateway

### "Module not found" errors
- Run `npm install` to install dependencies
- Delete `node_modules` and `.next` folders, then reinstall

### Charts not rendering
- Verify data format matches Recharts requirements
- Check browser console for errors
- Ensure data is not empty

### Build fails
- Run `npm run type-check` to identify TypeScript errors
- Check for missing dependencies
- Verify all imports are correct

## 📝 License

Part of the OMARINO EMS Suite. See main repository for license information.

## 🤝 Contributing

This is part of the larger OMARINO EMS project. See the main repository for contribution guidelines.

## 📞 Support

For issues and questions, please refer to the main OMARINO EMS repository.
