using AutoMapper;
using DCDS.Application.Dtos.Requests;
using DCDS.Infra.Models;

namespace DCDS.Infra.Profiles
{
    public class UserProfile : Profile
    {
        public UserProfile()
        {
            CreateMap<CreateUserRequest, User>();
        }
    }
}
