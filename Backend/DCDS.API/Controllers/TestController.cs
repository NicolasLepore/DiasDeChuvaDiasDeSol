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
        public ActionResult GetTest()
        {
            return Ok(new { Message = "Hello World", Status = StatusCodes.Status200OK });
        }
    }
}
