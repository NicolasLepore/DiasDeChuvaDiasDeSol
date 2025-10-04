using AutoMapper;
using DCDS.Application.Dtos.Requests;
using DCDS.Application.Interfaces;
using DCDS.Domain.Exceptions;
using DCDS.Infra.Models;
using Microsoft.AspNetCore.Identity;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace DCDS.Infra.Services
{
    public class AuthService : IAuthService
    {
        private readonly IMapper _mapper;
        private readonly UserManager<User> _userManager;
        private readonly SignInManager<User> _signInManager;

        public AuthService(IMapper mapper, UserManager<User> userManager, SignInManager<User> signInManager)
        {
            _mapper = mapper;
            _userManager = userManager;
            _signInManager = signInManager;
        }

        public void Logout()
        {
            throw new NotImplementedException();
        }

        public void SignInAsync()
        {
            throw new NotImplementedException();
        }

        public async Task<bool> SignUpAsync(CreateUserRequest dto)
        {
            var user = _mapper.Map<User>(dto);
            Console.WriteLine(user.UserName);
            var result = await _userManager.CreateAsync(user, dto.Password!);

            if (!result.Succeeded)
            {
                var errorsListMessage = "";
                foreach (var error in result.Errors)
                {
                    errorsListMessage += error.Description + "\n";
                }
                Console.WriteLine("LISTA ERROS: " + errorsListMessage);
                throw new AuthException("Failed to register user!", errorsListMessage);

            }

            return result.Succeeded;
        }
    }
}
