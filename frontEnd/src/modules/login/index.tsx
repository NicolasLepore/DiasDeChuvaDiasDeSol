import { GoLock } from "react-icons/go";
import { IoPerson } from "react-icons/io5";
import { useNavigate } from "react-router-dom";

const Login = () => {
  const navigate=useNavigate();
  const hundleCadastro =()=>{
    navigate("/cadastro")

  }
  return (
    <div className="flex w-full  lg:h-screen items-center justify-center bg-gradient-to-t from-[#AED9FF] via-[#cff3f8] to-[#ddebff] p-5">
      <div className=" lg:h-[75%]  bg-white lg:w-[30%] border-[0.1px] rounded-[10px] p-8 border-gray-400 flex ">
        <form className=" w-full rounded-xl flex flex-col  justify-around h-[80%] lg:gap-5">
          <h1 className="text-center font-bold text-2xl">
            Seja bem-vindo de volta!
          </h1>
          <div>
            <label className="font-semibold p-4 text-sm" htmlFor="name">
              Email ou Usuário
            </label>
            <div className="relative">
              <IoPerson className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                placeholder=" seu@Email.com"
                className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300 "
              />
            </div>
          </div>

          <div>
            <label className="font-semibold p-4 text-sm " htmlFor="psswd">
              Senha
            </label>
            <div className="relative">
              <GoLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                placeholder="Digite sua senha"
                className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300 "
              />
            </div>
            <p className="text-end text-[#3182fe]">Esqueceu a senha?</p>
            <div className="my-11 flex flex-col gap-8">
              <button className="w-full h-5 p-5 flex items-center justify-center bg-gradient-to-r rounded-3xl from-[#8EBFFC] via-[#79D3DC] to-[#79E2A8] text-white ">
              Entrar
              </button>
              <p className="text-center text-sm">Novo no DCDS?<span onClick={hundleCadastro} className="text-[#3182fe] text-sm">Cadastrar-se</span></p>
            </div>
          </div>
        </form>
        <div></div>
      </div>
    </div>
  );
};

export default Login;
