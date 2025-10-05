/* import { VscAccount } from "react-icons/vsc";  */
import { Calendar } from "lucide-react";
import { useNavigate } from "react-router-dom";
import banner from "../../assets/banner.png";
import img1 from "../../assets/img1.png";
import img2 from "../../assets/img2.png";

const Home = () => {
  const navigate = useNavigate();

  const hundleClima = () => {
    navigate("/clima");
  };

  const hundleLogin = () => {
    navigate("/login");
  };

  return (
    <main className="w-screen flex p-10 flex-col justify-around sm:p-6 md:p-10 bg-gradient-to-t from-[#F8FBFF] via-[#FFEDDB] to-[#FFDFD2]">
      {/* Título e banner */}
      <div className="text-center font-bold w-full flex flex-col sm:gap-8 md:gap-10">
        <div className="text-2xl sm:text-3xl md:text-4xl text-black leading-snug">
          Planeje Seu dia com o <span className="text-blue-600">clima</span> a
          Seu Favor
        </div>

        <div className="flex justify-center">
          <img
            src={banner}
            alt="Banner"
            className="w-full max-w-[87rem] sm:h-64 md:h-80 lg:h-96 object-cover rounded-2xl shadow-md"
          />
        </div>
      </div>

      {/* Botões principais */}
      <div className="flex flex-col  sm:flex-row justify-around gap-6 items-center  sm:gap-10 p-6 sm:p-6 mt-[40px] w-full ">
        <button className="flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-3 bg-[#F5FAF9] rounded-full shadow-md text-black hover:bg-black hover:text-white transition text-base sm:text-lg">
          <Calendar className="w-5 h-5 sm:w-6 sm:h-6 text-red-500" />
          <span className="font-medium">Agendar evento</span>
        </button>

        <button
          onClick={hundleClima}
          className="flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-3 bg-black rounded-full shadow-md text-white hover:bg-white hover:text-black transition text-base sm:text-lg"
        >
          <Calendar className="w-5 h-5 sm:w-6 sm:h-6 text-red-500" />
          <span className="font-medium">Clima atual</span>
        </button>
      </div>

      {/* Seções de conteúdo */}
      <div className="grid  sm:gap-12 gap-5  sm:p-6 md:p-8 sm:mt-10 ">
        {/* Bloco 1 */}
        <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-6  p-6 bg-[#F5FAF9] rounded-xl shadow-md">
          <img src={img1} className="w-full rounded-md object-cover " alt="" />
          <div>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-semibold">
              Veja o <span className="text-blue-600">clima</span> com
              antecedência
            </h2>
            <p className="mt-3 text-gray-600 text-base sm:text-lg md:text-2xl leading-relaxed">
              Mussum Ipsum, cacilds vidis litro abertis. Mais vale um bebadis
              conhecidis, que um alcoolatra anonimis. Mauris nec dolor in eros
              commodo tempor. Aenean aliquam molestie leo, vitae iaculis nisl.
              Tá deprimidis, eu conheço uma cachacis que pode alegrar sua vidis.
            </p>
          </div>
        </div>

        {/* Bloco 2 */}
        <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-6 bg-[#F5FAF9] p-6 rounded-xl shadow-md">
          <div>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-semibold">
              Organize seus compromissos aqui
            </h2>
            <p className="mt-3 text-gray-600 text-base sm:text-lg md:text-2xl leading-relaxed">
              Mussum Ipsum, cacilds vidis litro abertis. Mais vale um bebadis
              conhecidis, que um alcoolatra anonimis. Mauris nec dolor in eros
              commodo tempor. Aenean aliquam molestie leo, vitae iaculis nisl.
              Tá deprimidis, eu conheço uma cachacis que pode alegrar sua vidis.
            </p>
            <button
              onClick={hundleLogin}
              className="mt-4 flex items-center gap-2 px-6 py-2 bg-black text-white rounded-full shadow-md hover:shadow-lg transition text-base sm:text-lg"
            >
              <span>Começar</span>
            </button>
          </div>
          <img src={img2} className="w-full rounded-md object-cover  " alt="" />
        </div>
      </div>
    </main>
  );
};

export default Home;
