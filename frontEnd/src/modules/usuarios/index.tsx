import { useEffect, useState } from "react"
import type { Person } from "../../API/interfaces";
import { getAllUsers } from "../../API/apibase";

const Usuarios = ()=>{

const [usuario, setUsuarios]=useState<Person[]>([]) 

const getUser = async () => {
    try {
      const response: any = await getAllUsers();
      
      setUsuarios(response);
    } catch (error) {
      
    }
  };


useEffect(() => {
    getUser();

  return () => {
  };
}, []);

    
    
    return(
        <div>
            {usuario.map((items, index)=>(
                <ul className=" bg-purple-500" key={index}>
                    <li>{items.email}</li>
                    <li>{items.username}</li>
                </ul>
            ))}




        </div>
    )
}

export default Usuarios; 