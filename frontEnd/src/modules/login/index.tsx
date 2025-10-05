import { GoLock } from "react-icons/go";
import { IoPerson } from "react-icons/io5";
import { useNavigate } from "react-router-dom";
import { Formik, Form, Field } from "formik";

const Login = () => {
  const navigate = useNavigate();

  const handleCadastro = () => {
    navigate("/cadastro");
  };

  return (
    <div className="flex w-full min-h-screen items-center justify-center bg-gradient-to-t from-[#AED9FF] via-[#CFF3F8] to-[#DDEBFF] p-5">
      <div className="bg-white w-full max-w-md rounded-xl shadow-lg border border-gray-300 p-8">
        <Formik
          initialValues={{
            user: "",
            password: "",
          }}
          onSubmit={(values) => {
            // 👉 Você adiciona sua lógica de submit aqui
            console.log(values);
          }}
        >
          {() => (
            <Form className="flex flex-col gap-6">
              <h1 className="text-center font-bold text-2xl text-gray-700">
                Seja bem-vindo de volta!
              </h1>

              {/* Campo de usuário/email */}
              <div>
                <label className="font-semibold text-sm block mb-2" htmlFor="user">
                  Email ou Usuário
                </label>
                <div className="relative">
                  <IoPerson className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                  <Field
                    id="user"
                    name="user"
                    type="text"
                    placeholder="seu@email.com"
                    className="w-full p-3 pl-10 rounded-3xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#8EBFFC] transition-all"
                  />
                </div>
              </div>

              {/* Campo de senha */}
              <div>
                <label className="font-semibold text-sm block mb-2" htmlFor="password">
                  Senha
                </label>
                <div className="relative">
                  <GoLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                  <Field
                    id="password"
                    name="password"
                    type="password"
                    placeholder="Digite sua senha"
                    className="w-full p-3 pl-10 rounded-3xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#79E2A8] transition-all"
                  />
                </div>
                <p className="text-end text-[#3182fe] text-sm mt-1 cursor-pointer hover:underline">
                  Esqueceu a senha?
                </p>
              </div>

              {/* Botão Entrar */}
              <button
                type="submit"
                className="w-full py-3 rounded-3xl bg-gradient-to-r from-[#8EBFFC] via-[#79D3DC] to-[#79E2A8] text-white font-semibold shadow-md hover:opacity-90 transition-all"
              >
                Entrar
              </button>

              {/* Link de cadastro */}
              <p className="text-center text-sm text-gray-600">
                Novo no DCDS?{" "}
                <span
                  onClick={handleCadastro}
                  className="text-[#3182fe] font-medium cursor-pointer hover:underline"
                >
                  Cadastrar-se
                </span>
              </p>
            </Form>
          )}
        </Formik>
      </div>
    </div>
  );
};

export default Login;
