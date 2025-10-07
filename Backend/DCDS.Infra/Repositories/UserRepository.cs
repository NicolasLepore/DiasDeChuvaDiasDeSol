using DCDS.Application.Repositories;
using DCDS.Infra.Data.Identity;
using DCDS.Infra.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace DCDS.Infra.Repositories
{
    public class UserRepository : IRepository<User>
    {
        private readonly UserContext _userContext;

        public UserRepository(UserContext userContext)
        {
            _userContext = userContext;
        }

        public IEnumerable<User> GetAll()
        {
            return _userContext.Users.ToList();
        }

         
    }
}
