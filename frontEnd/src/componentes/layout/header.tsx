import { useState } from "react";
import { VscAccount } from "react-icons/vsc";
import { useNavigate } from "react-router-dom";

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const handleMenuToggle = () => {
    setMenuOpen(!menuOpen);
  };

  const hundleHome = () => {
    navigate("/");
  };

  const hundleCalendar = () => {
    navigate("/calendar");
  };

  const hundleLogin = () => {
    navigate("/login");
  };
  const hundleClima = () => {
    navigate("/clima");
  };
  return (
    <>
      <header className="bg-black text-white flex items-center justify-between px-4 py-3 md:px-8 lg:px-12 relative z-20">
        <VscAccount className="text-2xl md:text-3xl" />

        {/* Menu normal (desktop/tablet) */}
        <div className="hidden md:flex justify-around md:w-[60%] lg:w-[40%] text-sm md:text-base lg:text-lg">
          <button onClick={hundleHome} className="hover:text-amber-100">
            Home
          </button>

          <button onClick={hundleClima} className="hover:text-amber-100">
            Clima
          </button>

          <button onClick={hundleCalendar} className="hover:text-amber-100">
            Calendário
          </button>

          <button onClick={hundleLogin} className="hover:text-amber-100">
            Login
          </button>
        </div>

        {/* Ícone de menu (mobile) */}
        <button onClick={handleMenuToggle} className="md:hidden text-3xl">
          ☰
        </button>
      </header>

      {/* Sidebar (mobile) */}
      {/* <div
        className={`fixed top-0 right-0 h-full w-2/3 bg-black text-white flex flex-col items-center justify-center gap-6 text-xl transition-transform duration-300 z-10 ${
          menuOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <button
          onClick={handleMenuToggle}
          className="absolute top-4 right-6 text-3xl"
        >
          ✕
        </button>

        <button onClick={hundleHome} className="hover:text-amber-100">
          Home
        </button>
        <button onClick={hundleClima} className="hover:text-amber-100">Clima</button>
        <button className="hover:text-amber-100">Calendário</button>
        <button onClick={hundleLogin} className="hover:text-amber-100">
          Login
        </button>
      </div> */}
      <div
        className={`fixed top-0 right-0 h-[80%] w-2/3 sm:w-1/4 
          bg-gradient-to-b from-[#FFF5EE] via-[#FFE1CC] to-[#FFD8C2]
          text-gray-800 shadow-xl flex flex-col items-center justify-center gap-8 text-xl font-semibold
          transition-transform duration-300 ease-in-out rounded-l-xl backdrop-blur-md z-50
          ${menuOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        {/* Botão de Fechar */}
        <button
          onClick={handleMenuToggle}
          className="absolute top-4 right-5 text-3xl text-gray-700 hover:rotate-90 transition-transform duration-300"
        >
          ✕
        </button>

        {/* Links */}
        <button
          onClick={() => {
            hundleHome();
            handleMenuToggle();
          }}
          className="w-3/4 pb-2 border-b border-gray-300 hover:text-amber-600 transition duration-300"
        >
          Home
        </button>

        <button
          onClick={() => {
            hundleClima();
            handleMenuToggle();
          }}
          className="w-3/4 pb-2 border-b border-gray-300 hover:text-amber-600 transition duration-300"
        >
          Clima
        </button>

        <button
          onClick={() => {
            // aqui você adiciona a função correspondente se tiver
            handleMenuToggle();
          }}
          className="w-3/4 pb-2 border-b border-gray-300 hover:text-amber-600 transition duration-300"
        >
          Calendário
        </button>

        <button
          onClick={() => {
            hundleLogin();
            handleMenuToggle();
          }}
          className="w-3/4 pb-2 border-b border-gray-300 hover:text-amber-600 transition duration-300"
        >
          Login
        </button>
      </div>
    </>
  );
}
