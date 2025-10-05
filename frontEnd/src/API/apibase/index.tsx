import axios from "axios"
import type { Person } from "../interfaces"



 export async function getAllUsers() {
    const response = await axios.get("http://localhost:5000/api/v1/auth/getusers")
    return response.data 
 
} 
export async function createUser({username, email, password, rePassword, birthday}:Person ){
     const response = await axios.post("localhost:5000/api/v1/auth/signup", {
      username: username,
      password: password,
      rePassword: rePassword,
      email: email,
      birthday: birthday,
    });
    return response.data

} 