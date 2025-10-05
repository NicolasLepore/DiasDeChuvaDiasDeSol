// Ajuste o caminho da importação abaixo para onde sua interface realmente está
import React from "react";
import { FaLock } from "react-icons/fa";
import { IoPerson } from "react-icons/io5";
import { MdOutlineEmail } from "react-icons/md";
import { useNavigate } from "react-router-dom";
import { Formik, Form, Field, ErrorMessage } from "formik";
import * as Yup from "yup";
import type { Person } from "../../API/interfaces";
import { createUser } from "../../API/apibase";

const Cadastro: React.FC = () => {
  const navigate = useNavigate();

  const initialValues: Person = {
    username: "",
    email: "",
    password: "",
    rePassword: "",
  };

  const validationSchema = Yup.object({
    username: Yup.string().required("O nome de usuário é obrigatório."),
    email: Yup.string()
      .email("Email inválido.")
      .required("O email é obrigatório."),
    password: Yup.string()
      .min(8, "A senha deve ter pelo menos 8 caracteres.")
      .matches(/[A-Z]/, "A senha deve ter ao menos uma letra maiúscula.")
      .matches(/[0-9]/, "A senha deve conter ao menos um número.")
      .matches(
        /[!@#%&]/,
        "A senha deve conter ao menos um símbolo (! @ # % &)."
      )
      .required("A senha é obrigatória."),
    rePassword: Yup.string()
      .oneOf([Yup.ref("password")], "As senhas não coincidem.")
      .required("Confirme sua senha."),
  });

  const handleLogin = () => {
    navigate("/login"); // ajuste a rota conforme seu app
  };

  const handleSubmit = async (values: Person) => {
    try {
      const response = await createUser({
        username: values.username,
        email: values.email,
        password: values.password,
        rePassword: values.rePassword, // ⚠ mapear rePassword → rePassword
      });
      console.log(response);
      alert("Cadastro realizado com sucesso!");
    } catch (err: any) {
      if (err.response) {
        console.log("Erro da API:", err.response.data);
      } else {
        console.log("Erro na requisição:", err.message);
      }
    }
  };
  return (
    <div className="flex w-full h-screen items-center justify-center bg-gradient-to-t from-[#AED9FF] via-[#cff3f8] to-[#ddebff]">
      <div className="bg-white border-[0.1px] rounded-[10px] p-8 border-gray-400 flex">
        <Formik
          initialValues={initialValues}
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
        >
          {({ isSubmitting }) => (
            <Form className="h-[70%] rounded-xl flex flex-col justify-around gap-5">
              <h1 className="text-center font-bold text-2xl">
                Seja bem-vindo ao D<span className="text-cyan-500">C</span>D
                <span className="text-cyan-500">S</span>
              </h1>

              {/* Usuário */}
              <div>
                <label className="font-semibold p-4 text-sm" htmlFor="username">
                  Usuário
                </label>
                <div className="relative">
                  <IoPerson className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                  <Field
                    type="text"
                    id="username"
                    name="username"
                    placeholder="Nome de usuário"
                    className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300"
                  />
                </div>
                <ErrorMessage
                  name="username"
                  component="div"
                  className="text-red-500 text-xs mt-1 pl-5"
                />
              </div>

              {/* Email */}
              <div>
                <label className="font-semibold p-4 text-sm" htmlFor="email">
                  Email
                </label>
                <div className="relative">
                  <MdOutlineEmail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                  <Field
                    type="email"
                    id="email"
                    name="email"
                    placeholder="Endereço de email"
                    className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300"
                  />
                </div>
                <ErrorMessage
                  name="email"
                  component="div"
                  className="text-red-500 text-xs mt-1 pl-5"
                />
              </div>

              {/* Senha */}
              <div>
                <label className="font-semibold p-4 text-sm" htmlFor="password">
                  Senha
                </label>
                <div className="relative">
                  <FaLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                  <Field
                    type="password"
                    id="password"
                    name="password"
                    placeholder="Digite sua senha"
                    className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300"
                  />
                </div>
                <ErrorMessage
                  name="password"
                  component="div"
                  className="text-red-500 text-xs mt-1 pl-5"
                />
              </div>

              {/* Confirmar Senha */}
              <div>
                <label
                  className="font-semibold p-4 text-sm"
                  htmlFor="rePassword"
                >
                  Confirmar senha
                </label>
                <div className="relative">
                  <FaLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                  <Field
                    type="password"
                    id="rePassword"
                    name="rePassword"
                    placeholder="Digite sua senha novamente"
                    className="w-full h-5 bg-white p-5 pl-9 rounded-3xl border-[1px] border-gray-300"
                  />
                </div>
                <ErrorMessage
                  name="rePassword"
                  component="div"
                  className="text-red-500 text-xs mt-1 pl-5"
                />

                {/* Regras de senha */}
                <div className="flex flex-col my-2 gap-7">
                  <div className="text-[10px] text-gray-600 italic">
                    <p className="pl-5">
                      Para garantir a segurança da sua conta, sua senha deve
                      conter:
                    </p>
                    <ul className="pl-6 list-disc">
                      <li>No mínimo 8 caracteres;</li>
                      <li>Pelo menos 1 letra maiúscula (A-Z)</li>
                      <li>Pelo menos 1 número (0-9)</li>
                      <li>Pelo menos 1 símbolo (ex: ! @ # % &)</li>
                    </ul>
                  </div>

                  {/* Botão */}
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full h-5 p-5 flex items-center justify-center bg-gradient-to-r from-[#8EBFFC] via-[#79D3DC] to-[#79E2A8] rounded-3xl text-white disabled:opacity-60"
                  >
                    {isSubmitting ? "Cadastrando..." : "Cadastrar"}
                  </button>

                  <p className="text-sm text-center">
                    Já usa o DCDS?
                    <span
                      className="text-[#3182fe] cursor-pointer"
                      onClick={handleLogin}
                    >
                      {" "}
                      Logar na conta
                    </span>
                  </p>
                </div>
              </div>
            </Form>
          )}
        </Formik>
      </div>
    </div>
  );
};

export default Cadastro;
