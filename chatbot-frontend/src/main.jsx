import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";

import './index.css'
import App from './App.jsx'
import FaqAdmin from './FaqAdmin.jsx';
import "bootstrap/dist/css/bootstrap.min.css";

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/*チャット画面*/}
        <Route path="/" element={<App/>} /> 

        {/*FAQ管理画面*/}
        <Route path="/admin/faqs" element={<FaqAdmin />}/>

      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
