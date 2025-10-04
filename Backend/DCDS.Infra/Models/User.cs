using Microsoft.AspNetCore.Identity;

namespace DCDS.Infra.Models
{
    public class User : IdentityUser
    {
        public User() : base()
        {
            
        }

        public DateTime Birthday { get; set; }
    }
}
