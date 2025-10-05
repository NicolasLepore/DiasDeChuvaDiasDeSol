import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "./modules/home";
import Login from "./modules/login";
import Layout from "./componentes/layout";
 

function App() {
  return (
    <>
      <BrowserRouter>
        <Layout> 
          <Routes>
            <Route element={<Home />} path={"/"} />
            <Route element={<Login />} path={"/login"} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </>
  );
}

export default App;
