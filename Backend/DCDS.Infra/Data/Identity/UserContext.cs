using DCDS.Infra.Models;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace DCDS.Infra.Data.Identity
{
    public class UserContext : IdentityDbContext<User>
    {
        public UserContext
            (DbContextOptions<UserContext> options) : base(options)
        { }

    }
}
