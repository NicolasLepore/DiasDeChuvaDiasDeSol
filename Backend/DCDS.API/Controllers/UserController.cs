using DCDS.Application.Dtos.Requests;
using DCDS.Application.Repositories;
using DCDS.Application.UseCases;
using DCDS.Infra.Models;
using Microsoft.AspNetCore.Mvc;

namespace DCDS.API.Controllers
{
    [ApiController]
    [Route("/api/v1/auth")]
    public class UserController : ControllerBase
    {
        private readonly UserUseCase _userUseCase;
        private readonly IRepository<User> _userRepository;

        public UserController(UserUseCase userUseCase, IRepository<User> repo)
        {
            _userUseCase = userUseCase;
            _userRepository = repo;
        }

        [HttpPost("signup")]
        public async Task<IActionResult> SignUpAsync([FromBody] CreateUserRequest request)
        {
            var response = await _userUseCase.RegisterAsync(request);

            if (!response.Success) return BadRequest("An unexpected error occurred");

            // retornar token
            return Ok("Success in creating the account");
        }

        [HttpPost("signin")]
        public async Task<IActionResult> SignInAsync([FromBody] SignInUserRequest request)
        {
            var response = await _userUseCase.LoginAsync(request);

            if(!response.Success) return BadRequest("An unexpected error occurred");

            return Ok(response);
        }

        [HttpGet("getusers")]
        public IActionResult GetUsers()
        {
            return Ok(_userRepository.GetAll());
        }
    }
}