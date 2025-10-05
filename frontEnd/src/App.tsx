import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "./modules/home";
import Layout from "./componentes/layout";
import Login from "./modules/login";
import Cadastro from "./modules/cadastro";
import Clima from "./modules/Clima";
import Usuarios from "./modules/usuarios";
import Calendar from "./modules/calendar";

function App() {
  return (
    <>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route element={<Home />} path={"/"} />
            <Route element={<Calendar />} path={"/calendar"} />
            <Route element={<Login />} path={"/login"} />
            <Route element={<Cadastro />} path={"/cadastro"} />
            <Route element={<Clima />} path={"/clima"} />
            <Route element={<Usuarios />} path={"/usuarios"} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </>
  );
}

export default App;
