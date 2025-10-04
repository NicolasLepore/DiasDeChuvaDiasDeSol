using DCDS.Application.Dtos.Requests;
using DCDS.Application.Dtos.Responses;
using DCDS.Application.Interfaces;
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
            var success = await _auth.SignUpAsync(dto);
            
            if(success)
            {
                var response = new DefaultResponseData()
                {
                    Success = true,
                    StatusCode = 200,
                };

                return response;
            }

            return new DefaultResponseData()
            {
                Success = false,
                StatusCode = 401
            };
        }
    }
}
