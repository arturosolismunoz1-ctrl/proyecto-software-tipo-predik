# ROLLBACK SNAPSHOT
Snapshot generado antes de implementación del Dashboard — 2026-06-25

---

## 1. Archivos en frontend/src/ (antes de cambios)

```
src/.gitkeep
src/App.tsx
src/index.css
src/main.tsx
src/api/client.ts
src/components/AdminPanel.tsx
src/components/EconomicContextWidget.tsx
src/components/KPIPanel.tsx
src/components/ResultsOverlay.tsx
src/components/wizard/WizardAnalisis.tsx
src/pages/LoginPage.tsx
src/pages/MapPage.tsx
src/store/useAuthStore.ts
src/types.ts
```

---

## 2. Contenido original de App.tsx

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './store/useAuthStore'
import LoginPage from './pages/LoginPage'
import MapPage from './pages/MapPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MapPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

---

## 3. Contenido original de main.tsx

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import L from 'leaflet'
import './index.css'
import App from './App.tsx'

// Fix Leaflet marker icons in Vite (webpack/vite asset handling issue)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

---

## 4. package.json (dependencies y devDependencies)

```json
{
  "dependencies": {
    "leaflet": "^1.9.4",
    "leaflet-draw": "^1.0.4",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-leaflet": "^4.2.1",
    "react-router-dom": "^6.24.1",
    "zustand": "^4.5.4"
  },
  "devDependencies": {
    "@types/geojson": "^7946.0.14",
    "@types/leaflet": "^1.9.12",
    "@types/leaflet-draw": "^1.0.9",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.40",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.3",
    "vite": "^5.3.4"
  }
}
```

---

## 5. Rutas de react-router-dom actuales

```
/login       → LoginPage
/            → MapPage (ProtectedRoute)
*            → Navigate to "/"
```

---

## 6. tailwind.config.js original

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#eef3fb',
          100: '#d0dfF3',
          200: '#a1bfe7',
          300: '#729fdb',
          400: '#437fcf',
          500: '#1a5fc3',
          600: '#144d9e',
          700: '#0f3b7a',
          800: '#0a2855',
          900: '#051631',
        },
      },
    },
  },
  plugins: [],
}
```

---

## Instrucciones de rollback

Para revertir todos los cambios:
1. Restaurar App.tsx con el contenido de este archivo
2. Restaurar main.tsx con el contenido de este archivo
3. Eliminar los archivos nuevos:
   - frontend/src/components/layout/AppSidebar.tsx
   - frontend/src/components/layout/AppTopbar.tsx
   - frontend/src/components/dashboard/DashboardPage.tsx
   - frontend/src/pages/DashboardHomePage.tsx
   - frontend/src/pages/AnalisisPage.tsx
   - frontend/src/pages/ProyectosPage.tsx
   - frontend/src/pages/ConsultaPage.tsx
   - frontend/src/pages/HistorialPage.tsx
   - frontend/src/pages/ConfigPage.tsx
4. Restaurar tailwind.config.js con el contenido de este archivo
5. Si se añadieron dependencias nuevas, ejecutar:
   npm uninstall react-grid-layout recharts lucide-react
6. Ejecutar npm install para restaurar estado limpio
7. Ejecutar npm run dev para verificar que todo funciona igual que antes
