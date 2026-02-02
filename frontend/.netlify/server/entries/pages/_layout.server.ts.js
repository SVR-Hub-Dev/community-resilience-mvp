const load = async (event) => {
  return {
    user: event.locals.user || null
  };
};
export {
  load
};
