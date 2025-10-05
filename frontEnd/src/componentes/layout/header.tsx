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

  const hundleLogin = () => {
    navigate("/login");
  };

  return (
    <>
      <header className="bg-black text-white flex items-center justify-between px-4 py-3 md:px-8 lg:px-12 relative z-20">
        <VscAccount className="text-2xl md:text-3xl" />

        {/* Menu normal (desktop/tablet) */}
        <ul className="hidden md:flex justify-around md:w-[60%] lg:w-[40%] text-sm md:text-base lg:text-lg">
          <button onClick={hundleHome} className="hover:text-amber-100">
            Home
          </button>
          <button className="hover:text-amber-100">Clima</button>
          <button className="hover:text-amber-100">Calendário</button>
          <button onClick={hundleLogin} className="hover:text-amber-100">
            Login
          </button>
        </ul>

        {/* Ícone de menu (mobile) */}
        <button onClick={handleMenuToggle} className="md:hidden text-3xl">
          ☰
        </button>
      </header>

      {/* Sidebar (mobile) */}
      <div
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
        <button className="hover:text-amber-100">Clima</button>
        <button className="hover:text-amber-100">Calendário</button>
        <button onClick={hundleLogin} className="hover:text-amber-100">
          Login
        </button>
      </div>
    </>
  );
}
