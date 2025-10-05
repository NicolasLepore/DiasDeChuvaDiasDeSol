using DCDS.Application.Dtos;
using System.IdentityModel.Tokens.Jwt;

namespace DCDS.Application.Interfaces
{
    public interface ITokenService
    {
        string CreateToken(UserDetail dto);
    }
}
