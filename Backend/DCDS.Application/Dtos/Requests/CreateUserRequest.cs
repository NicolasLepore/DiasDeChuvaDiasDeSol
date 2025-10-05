using System.ComponentModel.DataAnnotations;

namespace DCDS.Application.Dtos.Requests
{
    public class CreateUserRequest
    {
        [Required]
        [MaxLength(64)]
        public string? Username { get; set; }

        [Required]
        [MaxLength(32)]
        [DataType(DataType.EmailAddress)]
        public string? Email { get; set; }

        [Required]
        [MaxLength(16)]
        [DataType(DataType.Password)]
        public string? Password { get; set; }

        [Required]
        [MaxLength(16)]
        [Compare("Password")]
        public string? RePassword { get; set; }
    }
}
