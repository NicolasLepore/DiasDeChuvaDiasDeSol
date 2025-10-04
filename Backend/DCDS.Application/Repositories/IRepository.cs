namespace DCDS.Application.Repositories
{
    public interface IRepository<T>
    {
        public IEnumerable<T> GetAll();
    }
}
