using DCDS.Application.Dtos.Requests;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace DCDS.Application.Interfaces
{
    public interface IAuthService
    {
        Task<bool> SignUpAsync(CreateUserRequest dto);
        void SignInAsync();
        void Logout();
    }
}
