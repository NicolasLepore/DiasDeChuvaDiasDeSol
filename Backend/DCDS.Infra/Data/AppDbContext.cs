using DCDS.Domain.Models;
using Microsoft.EntityFrameworkCore;

namespace DCDS.Infra.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> opt) : base(opt)
        { }

        public DbSet<Teste> Testes { get; set; }
    }
}
