using DCDS.Application.Interfaces;
using DCDS.Application.Repositories;
using DCDS.Application.UseCases;
using DCDS.Infra.Data;
using DCDS.Infra.Data.Identity;
using DCDS.Infra.Models;
using DCDS.Infra.Repositories;
using DCDS.Infra.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace DCDS.API
{
    public class Program
    {
        public static void Main(string[] args)
        {
            var builder = WebApplication.CreateBuilder(args);

            // Add services to the container.

            builder.Services.AddControllers();
            // Learn more about configuring Swagger/OpenAPI at https://aka.ms/aspnetcore/swashbuckle
            builder.Services.AddEndpointsApiExplorer();
            builder.Services.AddSwaggerGen();

            builder.Services.AddAutoMapper(AppDomain.CurrentDomain.GetAssemblies());

            // DIs
            builder.Services.AddScoped<UserUseCase>();

            builder.Services.AddScoped<IRepository<User>, UserRepository>();
            builder.Services.AddScoped<IAuthService, AuthService>();

            string appConnString = builder.Configuration.GetConnectionString("AppConnectionString")!;

            string identityConnString = builder.Configuration.GetConnectionString("UserConnectionString")!;


            builder.Services.AddDbContext<UserContext>(opt =>
            {
                opt.UseMySql(identityConnString, ServerVersion.AutoDetect(identityConnString));
            });

            builder.Services.AddDbContext<AppDbContext>(opt =>
            {
                opt.UseMySql(appConnString, ServerVersion.AutoDetect(appConnString));
            });

            builder.Services
                .AddIdentity<User, IdentityRole>()
                .AddEntityFrameworkStores<UserContext>()
                .AddDefaultTokenProviders();

            builder.Services.Configure<IdentityOptions>(opt =>
            {
                opt.Password.RequireNonAlphanumeric = true;
                opt.Password.RequireDigit = true;
                opt.Password.RequireLowercase = true;
                opt.Password.RequireUppercase = true;
            });

            var app = builder.Build();

            // Configure the HTTP request pipeline.
            if (app.Environment.IsDevelopment())
            {
                app.UseSwagger();
                app.UseSwaggerUI();
            }

            app.UseHttpsRedirection();

            app.UseAuthorization();


            app.MapControllers();

            using(var scope = app.Services.CreateScope())
            {
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                var identityDb = scope.ServiceProvider.GetRequiredService<UserContext>();

                db.Database.Migrate();
                identityDb.Database.Migrate();
            }

            using(var scope = app.Services.CreateScope())
            {
                var userManager = scope.ServiceProvider.GetRequiredService<UserManager<User>>();
                string[] names = 
                    new string[5] { "Antonio", "Gustavo", "Henri", "Nicolas", "Rafael" };

                foreach(var name in names)
                {
                    var user = new User()
                    {
                        UserName = name,
                        Email = $"{name}" + "@gmail.com"
                    };

                    var result = userManager.CreateAsync(user, "123Senha!").Result;

                    if(!result.Succeeded)
                    {
                        Console.WriteLine($"Erro ao criar usuario {user.UserName}");
                    }
                }
            }

            app.Run();
        }
    }
}
