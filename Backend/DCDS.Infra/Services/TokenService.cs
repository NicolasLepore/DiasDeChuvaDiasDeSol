using DCDS.Application.Dtos;
using DCDS.Application.Interfaces;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;

namespace DCDS.Infra.Services
{
    public class TokenService : ITokenService
    {
        public string CreateToken(UserDetail dto)
        {
            Claim[] claims = new Claim[]
            {
                new Claim("id", dto.Id!),
                new Claim(ClaimTypes.Name, dto.UserName!),
                new Claim(ClaimTypes.DateOfBirth, dto.Birthday!)
            };

            var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes("xOP87MnBNKAppLHJam7333op19xJfwWq"));

            var signInCredentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

            var token = new JwtSecurityToken
                (
                    expires: DateTime.Now.AddHours(1),
                    claims: claims,
                    signingCredentials: signInCredentials
                );

            return new JwtSecurityTokenHandler().WriteToken(token);
        }
    }
}
