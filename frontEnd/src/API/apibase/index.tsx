import axios from "axios";
import type { Person } from "../interfaces";

export interface LoginData {
  username: string;
  password: string;
}

export async function login(values: LoginData) {
  const response = await axios.post(
    "http://localhost:5000/api/v1/auth/signin",
    values
  );
  return response.data;
}

export async function getAllUsers() {
  const response = await axios.get(
    "http://localhost:5000/api/v1/auth/getusers"
  );
  return response.data;
}
export async function createUser({
  username,
  email,
  password,
  rePassword,
}: Person) {
  const response = await axios.post(
    "http://localhost:5000/api/v1/auth/signup",
    {
      username: username,
      password: password,
      rePassword: rePassword,
      email: email,
    }
  );
  return response.data;
}


