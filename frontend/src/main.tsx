/**
 * main.tsx — Punto de entrada de la aplicación.
 * Monta el árbol React con los providers globales y el router.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { Providers } from './app/Providers'
import { AppRouter } from './routes/AppRouter'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Providers>
      <AppRouter />
    </Providers>
  </React.StrictMode>,
)
