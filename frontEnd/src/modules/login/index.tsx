import { FaLock } from "react-icons/fa";
import { IoPerson } from "react-icons/io5";
import { MdOutlineEmail } from "react-icons/md";

const Login = () => {
  return (
    <div className="flex w-full h-screen items-center justify-center bg-gradient-to-t from-[#AED9FF] via-[#cff3f8] to-[#ddebff]">
      <div className="   bg-white border-[0.1px] rounded-[10px] p-8 border-gray-400 flex ">
        <form className=" h-[70%] rounded-xl flex flex-col  justify-around gap-5 ">
          <h1 className="text-center font-bold text-2xl">
            Seja bem-vindo ao D<span className="text-cyan-500">C</span>D
            <span className="text-cyan-500">S</span>
          </h1>
          <div>
            <label className="font-semibold p-4 text-sm" htmlFor="name">
              Usuário
            </label>
           <div className="relative">
              <IoPerson className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                placeholder=" Nome de usuário"
                className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300 "
              />
            </div>
          </div>
          <div>
            <label className="font-semibold p-4 text-sm " htmlFor="email">
              Email
            </label>
            <div className="relative">
              <MdOutlineEmail  className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                placeholder="Endereço de email"
                className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300 "
              />
            </div>
          </div>
          <div>
            <label className="font-semibold p-4 text-sm " htmlFor="psswd">
              Senha
            </label>
            <div className="relative">
              <FaLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                placeholder="Digite sua senha"
                className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300 "
              />
            </div>
          </div>
          <div>
            <label className="font-semibold p-4 text-sm " htmlFor="psswd02">
              Confirmar senha
            </label>
            <div className="relative">
              <FaLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                placeholder="Digite sua senha novamente"
                className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300 "
              />
            </div>
            <div className="text-[10px] text-gray-600 italic ">
              <p className="pl-5">
                Para garantir a segurança da sua conta, sua senha deve conter:
              </p>
              <div className="pl-15">
                <li>No minimo 8 caracteres;</li>
                <li>Pelomenos 1 letra maiúscula (A-Z)</li>
                <li>Pelo menos 1 número (0-9) </li>
                <li>Pelo menos 1 símbolo (ex: ! @ # % &)</li>
              </div>
            </div>
          </div>
        </form>
        <div>
        </div>
      </div>
    </div>
  );
};

export default Login;
