using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DCDS.API.Controllers
{
    [ApiController]
    [Route("api/v1/test")]
    public class TestController : ControllerBase
    {

        public TestController()
        {
        }

        [HttpGet]
        [Authorize]
        public ActionResult GetTest()
        {
            return Ok(new { Message = "Endpoint protegido acessado!", Status = StatusCodes.Status200OK });
        }
    }
}
