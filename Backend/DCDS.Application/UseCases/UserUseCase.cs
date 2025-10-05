using DCDS.Application.Dtos.Requests;
using DCDS.Application.Dtos.Responses;
using DCDS.Application.Interfaces;
using DCDS.Domain.Exceptions;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace DCDS.Application.UseCases
{
    public class UserUseCase
    {
        private readonly IAuthService _auth;

        public UserUseCase(IAuthService auth)
        {
            _auth = auth;
        }

        public async Task<DefaultResponseData> RegisterAsync(CreateUserRequest dto)
        {
            var result = await _auth.SignUpAsync(dto);

            if (!result.Succeeded)
            {
                var errorsListMessage = "";
                foreach (var error in result.Errors)
                {
                    errorsListMessage += error.Description + "\n";
                }

                Console.WriteLine("Error list: " + errorsListMessage);
                throw new AuthException("Failed to register user!", errorsListMessage);

            }

            return new DefaultResponseData()
            {
                Success = false,
                StatusCode = 200
            };
        }

        public async Task<DefaultResponseData> LoginAsync(SignInUserRequest dto)
        {
            var result = await _auth.SignInAsync(dto);

            if(!result.Succeeded) throw new AuthException("Failed to signIn, invalid credentials!");

            return new DefaultResponseData()
            {
                Success = false,
                StatusCode = 200
            };
        }
    }
}
