import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "./modules/home";
import Layout from "./componentes/layout";
import Login from "./modules/login";
import Cadastro from "./modules/cadastro";
import Clima from "./modules/Clima";
import Usuarios from "./modules/usuarios";
import Calendar from "./modules/calendar";
import { PrivateRoute } from "./componentes/privateRoute";

function App() {
  return (
    <>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route element={<Login />} path={"/login"} />

            <Route element={<Home />} path={"/"} />

            <Route
              element={
                <PrivateRoute>
                  <Calendar />
                </PrivateRoute>
              }
              path={"/calendar"}
            />

            <Route
              element={
                
                  <Cadastro />
                
              }
              path={"/cadastro"}
            />

            <Route
              element={
                <PrivateRoute>
                  <Clima />
                </PrivateRoute>
              }
              path={"/clima"}
            />

            <Route
              element={
                
                  <Usuarios />
                
              }
              path={"/usuarios"}
            />
          </Routes>
        </Layout>
      </BrowserRouter>
    </>
  );
}

export default App;
