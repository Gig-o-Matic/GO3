from django.utils.functional import keep_lazy_text


@keep_lazy_text
def join_trans(joiner, str_list):
    """Join translatable strings as late as possible.

    Note that joiner must be a translation object.  If it's a Python string,
    this function runs too early."""
    return joiner.join(str(s) for s in str_list)
