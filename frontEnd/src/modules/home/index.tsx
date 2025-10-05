/* import { VscAccount } from "react-icons/vsc";  */
import { Calendar } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Home = () => {
  const navigate = useNavigate();

  const hundleLogin = () => {
    navigate("/login");
  };

  return (
    <div className="flex flex-col gap-6">
      <main className="w-screen flex-col ">
        <div className="text-center font-bold w-full flex flex-col gap-10  ">
          <div className="text-4xl text-black ">
            Planeje Seu dia com o <span className="text-blue-600">clima</span> a
            Seu Favor
          </div>
          <div className="flex justify-center ">
            <img src="/" width={1400} height={395} className="bg-gray-300" />
          </div>
        </div>
        <div className="flex justify-around p-10">
          <button className="flex items-center justify-center gap-2 w-full max-w-xs py-3 bg-[#F5FAF9] rounded-full shadow-md hover:bg-black">
            <Calendar className="w-6 h-6 text-red-500" />
            <span className="text-lg font-medium text-black">
              Agendar evento
            </span>
          </button>

          <button className="flex items-center justify-center gap-2 w-full max-w-xs py-3 bg-black rounded-full shadow-md hover:bg-white">
            <Calendar className="w-6 h-6 text-red-500" />
            <span className="text-lg font-medium text-white">Clima atual</span>
          </button>
        </div>
        <div className="grid gap-12 p-8">
          <div className="grid md:grid-cols-2 items-center gap-6 bg-[#F5FAF9] p-6 rounded-xl shadow-md">
            <div className="w-full h-52 bg-gray-300 rounded-md"></div>

            <div>
              <h2 className="text-xl font-semibold">
                Veja o <span className="text-blue-600">clima</span> com
                antecedência
              </h2>
              <p className="mt-2 text-gray-600">
                Mussum Ipsum, cacilds vidis litro abertis. Mais vale um bebadis
                conhecidis, que um alcoolatra anonimis. Mauris nec dolor in eros
                commodo tempor. Aenean aliquam molestie leo, vitae iaculis nisl.
                Tá deprimidis, eu conheço uma cachacis que pode alegrar sua
                vidis.
              </p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 items-center gap-6 bg-[#F5FAF9] p-6 rounded-xl shadow-md">
            <div>
              <h2 className="text-xl font-semibold">
                Organize seus compromissos aqui
              </h2>
              <p className="mt-2 text-gray-600">
                Mussum Ipsum, cacilds vidis litro abertis. Mais vale um bebadis
                conhecidis, que um alcoolatra anonimis. Mauris nec dolor in eros
                commodo tempor. Aenean aliquam molestie leo, vitae iaculis nisl.
                Tá deprimidis, eu conheço uma cachacis que pode alegrar sua
                vidis.
              </p>
              <button
                onClick={hundleLogin}
                className="mt-4 flex items-center gap-2 px-6 py-2 bg-black text-white rounded-full shadow-md hover:shadow-lg transition"
              >
                <span>Começar</span>
              </button>
            </div>

            <div className="w-full h-52 bg-gray-300 rounded-md"></div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home;
