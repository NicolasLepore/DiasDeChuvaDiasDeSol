using AutoMapper;
using DCDS.Application.Dtos;
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
        private readonly ITokenService _tokenService;
        private readonly UserManager<User> _userManager;
        private readonly SignInManager<User> _signInManager;

        public AuthService(IMapper mapper, UserManager<User> userManager, SignInManager<User> signInManager, ITokenService tokenService)
        {
            _mapper = mapper;
            _userManager = userManager;
            _signInManager = signInManager;
            _tokenService = tokenService;
        }

        public void Logout()
        {
            throw new NotImplementedException();
        }

        public async Task<string> SignInAsync(SignInUserRequest dto)
        {
            var result = await _signInManager.PasswordSignInAsync(dto.UserName!, dto.Password!, false, false);

            if (!result.Succeeded) throw new AuthException("Failed to signIn, invalid credentials!");

            var user =
                _signInManager
                .UserManager
                .Users
                .FirstOrDefault(user => user.UserName == dto.UserName);

            var userDetails = new UserDetail()
            {
                UserName = user.UserName,
                Id = user.Id,
                Birthday = user.Birthday.ToString()
            };

            var token = _tokenService.CreateToken(userDetails);

            return token;
        }

        public async Task<IdentityResult> SignUpAsync(CreateUserRequest dto)
        {
            var user = _mapper.Map<User>(dto);

            var result = await _userManager.CreateAsync(user, dto.Password!);

            return result;
        }
    }
}
