using DCDS.Application.Dtos.Requests;
using Microsoft.AspNetCore.Identity;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace DCDS.Application.Interfaces
{
    public interface IAuthService
    {
        Task<IdentityResult> SignUpAsync(CreateUserRequest dto);
        Task<string> SignInAsync(SignInUserRequest dto);
        void Logout();
    }
}
