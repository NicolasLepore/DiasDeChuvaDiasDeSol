using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace DCDS.Domain.Exceptions
{
    public class AuthException : Exception
    {

        public AuthException(string message) : base(message) { }
        public AuthException(string message, string errorListMessage) 
            : base(message + "\n" + errorListMessage) { }
        public AuthException(string message, Exception inner) : base(message, inner) { }
    }
}
